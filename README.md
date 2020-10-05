
# Custom callback plugin designed to send notification to MS Team

 Version | Date Modified | Comments          |
---------|---------------|-------------------|
1.0.0    | 04 Oct 2020   | Initial commit    |

## Introduction

This is an Ansible callback plugin specifically designed to send custom deployment notification to MS Team channel. It uses Jinja2 template for message card. See my blog [How to Write a Custom Ansible Callback Plugin to ost to MS Teams using Jinja2 Template as a Message Card][msteams_blog_url]

## Installation - General

1. Download this plugin under `<your playbook root directory>/callback_plugins` folder.
2. Whitelist the callback plugin in your `ansible.cfg` as shown below under the `[defaults]` section. If you have more than one callback plugins, separate them by comma (,)  
   `callback_whitelist = msteam`  
3. Ensure you have appropriate MS Team message card template to use.

## Installation - use git submodule

The following steps explains how you can use this plugin as `git submodule` that allows you to use the plugin but not to maintain in your repository and always get the version you need.  

### Cloning callback_plugin repository as a submodule in your playbook repository

1. Open `git bash` and change to your playbook repository. In the example below, I'm clonning it as submodule in my playbook `ansible_msteam_callback_plugin_using_jinja2_template_example`:  
   ```bash
   cd ~/workspace/ansible_msteam_callback_plugin_using_jinja2_template_example
   ``` 
2. Clone `callback_plugins` repository as a submodule in your repository. For example:  
   ```bash
   git submodule add https://github.com/pppoudel/callback_plugins.git
   ```
3. It creates `callback_plugins` directory and `.gitmodules` file in your repository  
4. Update the submodule config to get from desired branch. For now, here I'm configuring `master` branch.  
   ```bash 
   git config -f .gitmodules submodule.callback_plugins.branch main
   ```
5. Add, commit, and push the submodule related configuration changes. For example: 
   ```bash 
   git add .gitmodules callback_plugins
   git commit -m "Added callback_plugins"
   git push -u origin <your branch>
   ```

### Whitelist the `msteam` plugin

1. Open `ansible.cfg` file located under your repository  
2. Add or update the following under the `[defaults]` section:  
   `callback_whitelist = msteam`  
3. Add, commit and push the `ansible.cfg` file
   ```bash
   git add ansible.cfg
   git commit -m "Whitelisted ms teams plugin"
   #git push -u origin "<your branch>"
   git push -u origin master
   ```

Once the above steps are done, you can sync the Ansible Tower Project for your playbook and test.

## Parameters as Playbook Extra-Vars

This plugin can be managed by the following ansible extra-vars passed to your playbook.

| Variable                        | Type          | Mandatory | Example   |
| ------------------------------- | ------------- | --------- | --------- |
| ``v_success_channel_url``       | String        | No (uses default if not provided) | ``"v_success_channel_url": "<success channel url>"`` |
| ``v_failure_channel_url``       | String        | No (uses default if not provided) | ``"v_failure_channel_url": "<failure channel url"`` |
| ``v_msteam_channel_url``        | String        | No (Overrides the default channel url value). | ``"v_msteam_channel_url": "<webhook url>"`` |
| ``v_message_template``          | String        | No (uses default if not provided)  | ``"v_message_template": "templates/msteam_deploy_msg.json.j2"`` |
| ``v_disable_msteam_post``       | String        | No (default 'No'). Another way to disable posting to MS Teams. | ``"v_disable_msteam_post": "Yes"``.  |

## How to get updates from submodule

If you decide to use this plugin as `git submodule`. Here is how you can get the updates.  

1. Open `git bash` and change to your playbook repository directory and run the commands listed below. In the example below, I'm getting updates for my playbook `ansible_msteam_callback_plugin_using_jinja2_template_example`:  
   ```bash
   cd ~/workspace/ansible_msteam_callback_plugin_using_jinja2_template_example
   git submodule update --remote
   # run git status to see if there is any change in submodule
   git status
   # if there is any change, add the submodule change, commit and push. For example
   git add callback_plugins
   git commit -m "Accepting and adding the latest from callback_plugins"
   #git push -u origin <your branch>
   git push -u origin master
   ```
[msteams_blog_url]: https://purnapoudel.blogspot.com/2020/10/how-to-write-ansible-callback-plugin.html