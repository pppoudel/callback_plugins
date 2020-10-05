#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function)
from ansible.plugins.callback import CallbackBase
from jinja2 import Template
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils._text import to_native
from tempfile import SpooledTemporaryFile

import json
import sys
import os
import datetime
import time
import requests
import re
from pytz import timezone

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

__metaclass__ = type


# Ansible documentation of the module.
DOCUMENTATION = '''
  msteam: Can send custom message to MS Team channel using pre-defined MS Team message card as Jinja2 template
  short_description: msteam is an Ansible callback plugin intended for use to send message to MS Team channel.
  author: Purna Poudel <purna.poudel@gmail.com>
'''


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'msteam'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.playbook_name = None
        self.tz = timezone('Canada/Eastern')
        self.dt_format = "%Y-%m-%d %H:%M:%S"
        self.start_time = datetime.datetime.now(self.tz)
        self.extra_vars = None
        # If you are executing your playbook from AWX/Tower
        # Replace with your Ansible Tower/AWX base url
        #self.v_at_base_url = "https://myawx"
        # The following variable is used to drive logic based on whether the playbook is executed from Tower or command line.
        # By default assume it is executed from command line
        self.executed_from_tower = False
        # To record whether the playbook variables are retrieved, so that we retrieve them just once.
        self.pb_vars_retrieved = False
        # default msteam url
        self.v_msteam_channel_url = "<replace with your default MS Team Webhook URL>"
        # default msteam message card template
        self.v_message_template = "templates/msteam_default_msg.json.j2"

        # default job status in the begining
        self.job_status = "successful"

        # If you need to post through proxies, uncomment the following and replace with your proxy URLs.
        # self.proxies = {
        #     "http": "<http-proxy-url>",
        #     "https": "<https-proxy-url>",
        # }

        # by default enable msteam notification
        self.disable_msteam_post = False
    # You can uncomment and customize the set_options method if needed.
    # def set_options(self, task_keys=None, var_options=None, direct=None):
    #     super(CallbackModule, self).set_options(
    #         task_keys=task_keys, var_options=var_options, direct=direct)

    def v2_playbook_on_start(self, playbook):
        display.vvv(u"v2_playbook_on_start method is being called")
        self.playbook = playbook
        self.playbook_name = playbook._file_name

    def v2_playbook_on_play_start(self, play):
        display.vvv(u"v2_playbook_on_play_start method is being called")
        self.play = play
        # get variable manager and retrieve extra-vars
        vm = play.get_variable_manager()
        self.extra_vars = vm.extra_vars
        self.play_vars = vm.get_vars(self.play)
        # The following is used to retrieve variables defined under group_vars or host_vars.
        # If the same variable is defined under both with the same scope, the one defined under host_vars takes precedence.
        self.host_vars = vm.get_vars()['hostvars']
        if not self.pb_vars_retrieved:
            self.get_pb_vars()

    # def v2_runner_on_failed(self, result, ignore_errors=False):
        #display.vvv(u"v2_runner_on_failed method is being called")

    # def v2_runner_on_unreachable(self, result):
    #     display.vvv(u"v2_runner_on_unreachable method is being called")

    # # Event used when host begins execution of a task from version 2.8
    # def v2_runner_on_start(self, host, task):
    #     display.vvv(u"v2_runner_on_start method is being called")

    # def v2_runner_on_ok(self, result, ignore_errors=False):
    #     display.vvv(u"v2_runner_on_ok method is being called")

    # def v2_runner_on_skipped(self, result):
    #     display.vvv(u"v2_runner_on_skipped is being called"

    def v2_playbook_on_stats(self, stats):
        display.vvv(u"v2_playbook_on_stats method is being called")
        if not self.pb_vars_retrieved:
            self.get_pb_vars()
        hosts = sorted(stats.processed.keys())
        self.hosts = hosts
        self.summary = {}
        self.end_time = datetime.datetime.now(self.tz)
        self.duration_time = int(
            (self.end_time - self.start_time).total_seconds())
        # Iterate trough all hosts to check for failures
        for host in hosts:
            summary = stats.summarize(host)
            self.summary = summary
            if summary['failures'] > 0:
                self.job_status = "failed"

            if summary['unreachable'] > 0:
                self.job_status = "failed"

            display.vvv(u"summary for host %s :" % host)
            display.vvv(str(summary))

            # Add code here if logging per host

        # Just send a single notification whether it is a failure or success
        # Post message to MS Team
        if(not self.disable_msteam_post):
            self.notify_msteam()
        else:
            display.vvv(u"Posting to MS Team has been disabled.")

    def get_pb_vars(self):
        display.vvv(u"get_pb_vars method is being called")
        self.pb_vars_retrieved = True

        try:
            self.tower_job_id = self.play_vars['tower_job_id']
            self.tower_job_template_name = self.play_vars['tower_job_template_name']
            self.scm_revision = self.play_vars['tower_project_revision']
            self.executed_from_tower = True
        except Exception as e:
            print("WARN: Playbook is not executed from Ansible Tower. Ansible Tower properties will not be available. Details %s" % str(e))
            self.tower_job_id = "na"
            self.tower_job_template_name = "na"
            self.scm_revision = "na"

        display.vvv(u"tower_job_id: %s" % self.tower_job_id)
        display.vvv(u"tower_job_template_name: %s" %
                    self.tower_job_template_name)
        display.vvv(u"scm_revision: %s" % self.scm_revision)
        display.vvv(u"executed_from_tower: %s" % self.executed_from_tower)

        # Extract common extra-vars

        try:
            _disable_msteam_post = self.extra_vars['v_disable_msteam_post']
            if(_disable_msteam_post.lower() == 'yes' or _disable_msteam_post.lower() == 'true'):
                self.disable_msteam_post = True
        except:
            display.vvv(
                u"Could not retrieve v_disable_msteam_post extra-vars from job")
            pass

        display.vvv(u"disable_msteam_post: %s" % self.disable_msteam_post)

        self.v_environment = "na"
        try:
            self.v_environment = self.extra_vars['v_environment']
        except:
            display.vvv(
                u"Could not retrieve v_environment extra-vars from job")
            pass

        display.vvv(u"v_environment: %s" % self.v_environment)

        self.v_app_file = "na"
        try:
            self.v_app_file = self.extra_vars['v_app_file']
        except:
            display.vvv(u"Could not retrieve v_app_file extra-vars from job")
            pass

        display.vvv(u"v_app_file: %s" % self.v_app_file)

        self.v_host_name = None
        try:
            self.v_host_name = self.extra_vars['v_host_name']
            display.vvv("v_host_name: %s" % self.v_host_name)
        except:
            display.vvv("Could not retrieve v_host_name extra-vars from job")
            pass

        display.vvv(u"v_host_name: %s" % self.v_host_name)

        self.v_deployment_action = "na"
        self.v_instance_name = "na"
        try:

            self.v_deployment_action = self.extra_vars['v_deployment_action']
        except:
            display.vvv(
                "Could not retrieve deployment related common extra-vars from job")
            pass

        try:
            self.v_instance_name = self.extra_vars['v_instance_name']
        except:
            display.vvv(
                "Could not retrieve WAS Liberty deployment specific extra-vars v_instance_name from job")
            pass

        display.vvv("v_deployment_action: %s" %
                    self.v_deployment_action)

        display.vvv("v_instance_name: %s" %
                    self.v_instance_name)

    def notify_msteam(self):
        display.vvv(u"notify_msteam method is being called")

        # check if default v_msteam_channel_url url is provided
        try:
            _v_msteam_channel_url = self.extra_vars['v_msteam_channel_url']
            if (_v_msteam_channel_url != "" and (_v_msteam_channel_url.lower() != "none")):
                self.v_msteam_channel_url = _v_msteam_channel_url
        except:
            display.vvv(
                u"v_msteam_channel_url is not passed as extra-vars. Will use default value: %s" % self.v_msteam_channel_url)
            pass

        # check if success channel url is provided
        v_success_channel_url = ""
        try:
            _v_success_channel_url = self.extra_vars['v_success_channel_url']
            if (_v_success_channel_url != "" and (_v_success_channel_url.lower() != "none")):
                v_success_channel_url = _v_success_channel_url
        except:
            display.vvv(
                u"v_success_channel_url is not passed as extra-vars. Will use default value: %s" % self.v_msteam_channel_url)
            pass

        # check if failure channel url is provided
        v_failure_channel_url = ""
        try:
            _v_failure_channel_url = self.extra_vars['v_failure_channel_url']
            if (_v_failure_channel_url != "" and (_v_failure_channel_url.lower() != "none")):
                v_failure_channel_url = _v_failure_channel_url
        except:
            display.vvv(
                u"v_failure_channel_url is not passed as extra-vars. Will use default value: %s" % self.v_msteam_channel_url)
            pass

        # check if message template is provided as extra-vars
        try:
            _v_message_template = self.extra_vars['v_message_template']
            if (_v_message_template != "" and (_v_message_template.lower() != "none")):
                self.v_message_template = _v_message_template
        except:
            display.vvv(
                u"v_message_template is not passed as extra-vars. Will use the default one")
            pass

        display.vvv("v_message_template: %s" %
                    self.v_message_template)

        # If you are using Ansible Tower/AWX and want to have reference back
        web_url = self.v_at_base_url + \
            "/#/jobs/playbook/"+str(self.tower_job_id)

        try:
            with open(self.v_message_template) as j2_file:
                template_obj = Template(j2_file.read())
        except Exception as e:
            print("ERROR: Exception occurred while reading MS Team message template %s. Exiting... %s" % (
                self.v_message_template, str(e)))
            sys.exit(1)

        rendered_template = template_obj.render(
            v_ansible_job_status=self.job_status,
            v_ansible_job_id=self.tower_job_id,
            v_ansible_scm_revision=self.scm_revision,
            v_ansible_job_name=self.tower_job_template_name,
            v_ansible_job_started=self.start_time.strftime(self.dt_format),
            v_ansible_job_finished=self.end_time.strftime(self.dt_format),
            v_ansible_job_elapsed_time=self.duration_time,
            v_ansible_host_list=self.hosts,
            v_ansible_web_url=web_url,
            v_ansible_app_file=self.v_app_file,
            v_ansible_deployment_action=self.v_deployment_action,
            v_ansible_environment=self.v_environment,
            v_ansible_instance_name=self.v_instance_name,
            v_ansible_executed_from_tower=self.executed_from_tower
        )

        try:
            with SpooledTemporaryFile(
                    max_size=0, mode='r+w') as tmpfile:
                tmpfile.write(rendered_template)
                tmpfile.seek(0)
                json_payload = json.load(tmpfile)
                display.vvv(json.dumps(json_payload))
        except Exception as e:
            print("ERROR: Exception occurred while reading rendered template or writing rendered MS Team message template. Exiting... %s" % str(e))
            sys.exit(1)

        if self.job_status == "successful":
            print("INFO: Sending success message to MS Team channel")
            if v_success_channel_url != "":
                self.v_msteam_channel_url = v_success_channel_url

        else:
            print("INFO: Sending failure message to MS Team channel")
            if v_failure_channel_url != "":
                self.v_msteam_channel_url = v_failure_channel_url

        display.vvv("v_msteam_channel_url: %s" % self.v_msteam_channel_url)

        try:
            # using proxy
            # response = requests.post(url=self.v_msteam_channel_url,
            #                          data=json.dumps(json_payload), headers={'Content-Type': 'application/json'}, timeout=10, proxies=self.proxies)

            # without proxy
            response = requests.post(url=self.v_msteam_channel_url,
                                     data=json.dumps(json_payload), headers={'Content-Type': 'application/json'}, timeout=10)

            if response.status_code != 200:
                raise ValueError('Request to msteam returned an error %s, the response is:\n%s' % (
                    response.status_code, response.text))
        except Exception as e:
            print(
                "WARN: Exception occurred while sending notification to MS team. %s" % str(e))
