# Capsule Installation Guide -- lab-capsule-6.deploy.crazy.lab

This document describes how to install and configure a Red Hat Satellite
Capsule server using the playbooks in this project.

## Prerequisites

- A running Satellite server (`lab-satellite-6.crazy.lab`) with content
  synced and lifecycle environments configured
- The Capsule host running RHEL 9 with network access to Red Hat CDN and
  the Satellite server
- SSH access to the Capsule host via `cloud-user` with passwordless sudo
- SSH access from the Ansible controller to the **Satellite server** (needed
  for automatic certificate generation)
- A valid Red Hat Satellite Capsule subscription

## Variable Files

| File | Purpose |
|------|---------|
| `00a_secrets.yml` | Vault-encrypted credentials (RHSM, Satellite admin, OAuth keys) |
| `00b_register_satellite.yml` | RHEL subscription and repository configuration |
| `00c_satellite_software_install.yml` | fapolicyd toggle and custom rules |
| `01a_capsule_installer_certificates.yml` | SSL certificates and cert-archive settings |
| `01b_capsule_firewall_rules.yml` | Firewalld ports and services |
| `01c_capsule_installer_configuration.yml` | Installer scenario, package name, and options |

## Preparation

### 1. Encrypt secrets

Replace all placeholder values in `00a_secrets.yml` with real vault-encrypted
values. Use the same vault password as the Satellite project:

```bash
ansible-vault encrypt_string 'value' --name 'variable_name'
```

At minimum you need:

- `satellite_rhsm_organization_id` / `satellite_rhsm_activationkey` -- Satellite org and activation key (the Capsule registers against the Satellite, not RHSM/CDN)
- `sat_initial_user` / `sat_initial_password` -- Satellite admin credentials
- `capsule_oauth_consumer_key` / `capsule_oauth_consumer_secret` -- from the Satellite:

```bash
# On the Satellite server:
grep oauth_consumer_key /etc/foreman/settings.yaml
grep oauth_consumer_secret /etc/foreman/settings.yaml
```

### 2. Verify SSL certificates

If you use custom SSL certificates (the same wildcard certificates as the
Satellite), ensure the `.pki/` directory contains the required files, or
update the paths in `01a_capsule_installer_certificates.yml`.

### 3. Review installer options

Check `01c_capsule_installer_configuration.yml` and adjust the installer
options to your environment. Key settings:

- `--foreman-proxy-foreman-base-url` -- must point to your Satellite
- `--foreman-proxy-trusted-hosts` -- must include your Satellite FQDN
- `--foreman-proxy-content-parent-fqdn` -- must point to your Satellite
- Service toggles (TFTP, HTTPBoot, templates, remote execution)

## Installation Steps

Run the following playbooks in order, limiting to the Capsule host:

### Step 1: Register the system

```bash
ansible-playbook 01_register_satellite.yml --limit lab-capsule-6.deploy.crazy.lab
```

Registers the Capsule host with Red Hat and enables the required
repositories (RHEL 9 BaseOS, AppStream, Satellite Capsule, Maintenance).

### Step 2: Install software and prepare the system

```bash
ansible-playbook 02_satellite_software_install.yml --limit lab-capsule-6.deploy.crazy.lab
```

Installs `satellite-capsule` package, optionally configures fapolicyd,
updates all packages, and reboots if necessary.

### Step 3: Run the Capsule installer

```bash
ansible-playbook 04_capsule_installer.yml --limit lab-capsule-6.deploy.crazy.lab
```

This playbook:

1. Deploys custom SSL certificates to the Capsule
2. **Automatically generates** the Capsule certificate archive by delegating
   `capsule-certs-generate` to `lab-satellite-6.crazy.lab` (the Satellite
   server), fetches the tar, and deploys it to the Capsule
3. Configures firewalld rules
4. Runs `satellite-installer --scenario capsule` with the configured options

**Note:** If the certificate archive already exists on the Satellite, it is
reused. To force regeneration, set `capsule_certs_regenerate: true` in
`01a_capsule_installer_certificates.yml`.

## Post-Installation

After the Capsule is installed, the following Satellite-side tasks may be
needed (run against the Satellite host, not the Capsule):

- Assign the Capsule to lifecycle environments
- Configure the Capsule as content source for subnets
- Add the Capsule to host groups as content source / puppet proxy

These are Satellite-level configuration changes in the Satellite's
`host_vars` (subnets, host groups) and re-running the corresponding
playbooks against the Satellite.

## Troubleshooting

**Certificate generation fails:**
Ensure the Ansible controller can SSH to `lab-satellite-6.crazy.lab` with
the same credentials. The `capsule-certs-generate` command requires root
access on the Satellite.

**Installer timeout:**
The default timeout is 3600 seconds (1 hour). For slow systems, increase
`satellite_installer_timeout` in `01c_capsule_installer_configuration.yml`.

**Firewall issues:**
Verify the ports listed in `01b_capsule_firewall_rules.yml` match the
Capsule documentation for your Satellite version.
