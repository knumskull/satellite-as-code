# Satellite as Code - CRAZY.LAB

Ansible project that fully automates the deployment and configuration of a
Red Hat Satellite 6 infrastructure, from initial RHEL registration through
content management, provisioning setup, and compliance scanning.

Every aspect of the Satellite configuration is expressed as code: playbooks
handle orchestration, while all environment-specific values live in
`host_vars` files, enabling clean separation between logic and data.

## Prerequisites

- **Control node**: Ansible 2.15+ (or AAP 2.x)
- **Target host**: RHEL 9 with network access to Red Hat CDN
- **Subscriptions**: Valid Red Hat Satellite subscription and manifest
- **Vault password**: Stored in `.vault.pass` (git-ignored) or provided via
  `--vault-password-file` / AAP credential

### Required Collections

| Collection | Purpose |
|---|---|
| `redhat.satellite` | Satellite resource management |
| `redhat.satellite_operations` | Satellite/Capsule installer |
| `redhat.rhel_system_roles` | RHEL registration (RHC) |
| `ansible.posix` | Firewalld configuration |

Install with:

```bash
ansible-galaxy collection install -r collections/requirements.yml
```

## Project Structure

```
.
├── site.yml                          # Full deployment (imports all playbooks in order)
├── 01_register_satellite.yml         # RHEL registration via RHC
├── 02_satellite_installer.yml        # Satellite server installation
├── 02_capsule_installer.yml          # Capsule server installation
├── 04_satellite_manifest.yml         # Manifest download and upload
├── 05_satellite_content_credentials.yml
├── 06_satellite_products_and_repositories.yml
├── 07_satellite_sync_repositories.yml
├── 08_satellite_sync_plans.yml
├── 09_satellite_lifecycle_environments.yml
├── 10_satellite_domains.yml
├── 11_satellite_subnets.yml
├── 12_satellite_content_views.yml
├── 13_satellite_content_view_publish.yml
├── 14_satellite_settings.yml
├── 16_satellite_operating_systems.yml
├── 17_satellite_activation_keys.yml
├── 18_satellite_host_groups.yml
├── 19_satellite_global_parameters.yml
├── 20_satellite_openscap.yml
├── 21_satellite_role.yml
├── 22_satellite_users.yml
├── inventory                         # Static inventory
├── ansible.cfg
├── host_vars/
│   └── lab-satellite-6.crazy.lab/    # All host-specific configuration
│       ├── 00a_secrets.yml           # Vault-encrypted credentials
│       ├── 00b_register_satellite.yml
│       ├── 01a_satellite_installer_certificates.yml
│       ├── 01b_satellite_firewall_rules.yml
│       ├── 01c_satellite_installer_configuration.yml
│       ├── 02_general.yml
│       ├── 03_cloud_connector.yml
│       ├── 04_manifest.yml
│       ├── 05_content_credentials.yml
│       ├── 06a_products.yml          # Red Hat products/repos
│       ├── 06b_custom_products.yml   # Custom products (EPEL)
│       ├── 06c_combined_products.yml # Merge of 06a + 06b
│       ├── 07_sync_plans.yml
│       ├── 08_lifecycle_environments.yml
│       ├── 09_domains.yml
│       ├── 10_subnets.yml
│       ├── 11a_content_views_custom_products.yml
│       ├── 11b_content_views.yml
│       ├── 11c_composite_content_views.yml
│       ├── 11d_rolling_content_views.yml
│       ├── 11e_combined_content_views.yml  # Merge of 11a-11d
│       ├── 12a-12g_settings_*.yml    # Satellite settings (split by area)
│       ├── 13_operating_systems.yml
│       ├── 14_activation_keys.yml
│       ├── 15a-15d_host_groups_*.yml # Host groups (layered hierarchy)
│       ├── 16a-16d_global_parameters_*.yml
│       ├── 17_openscap.yml
│       ├── 18_roles.yml
│       └── 19_users
└── group_vars/
    └── satellite-dev.yml             # Group-level overrides
```

## Playbook Execution Order

The playbooks are numbered to indicate their intended execution order. Run
them individually for targeted changes, or use `site.yml` for a full
deployment from scratch.

### Full Deployment

```bash
ansible-playbook site.yml
```

### Individual Playbooks

Run a single step when only specific configuration has changed:

```bash
ansible-playbook 14_satellite_settings.yml
```

### Execution Flow

```
01  Register Satellite host with Red Hat (RHC)
02  Install Satellite (certificates, firewall, packages, installer)
        │
04  Download and upload subscription manifest
05  Create content credentials (GPG keys)
06  Enable products and repositories
07  Synchronize repositories (async)
08  Create sync plans
        │
09  Create lifecycle environments
10  Create domains
11  Create subnets
        │
12  Create content views (regular, composite, rolling)
13  Publish and promote content views (async)
        │
14  Apply Satellite settings
16  Configure operating systems
17  Create activation keys
18  Create host groups (hierarchical)
19  Set global parameters
        │
20  Configure OpenSCAP (compliance policies)
21  Create Satellite roles
22  Create Satellite users
```

### Capsule Installation

To install a Satellite Capsule, add the Capsule host to the inventory under
a `[capsule]` group and provide appropriate `host_vars`:

```bash
ansible-playbook 02_capsule_installer.yml --limit lab-capsule-1.crazy.lab
```

The Capsule installer expects the same firewall and certificate variables as
the Satellite installer, plus `satellite_installer_scenario: capsule` and
a `satellite_installer_certs_tar_file` pointing to the certificate archive
generated on the Satellite server.

## Variable Organization

All environment-specific configuration lives in `host_vars`. The files use a
numbered naming convention that mirrors the playbook they feed into.

### Naming Convention

| Prefix | Area | Example |
|--------|------|---------|
| `00` | Secrets and registration | `00a_secrets.yml` |
| `01` | Installer (certs, firewall, options) | `01c_satellite_installer_configuration.yml` |
| `02` | General / shared variables | `02_general.yml` |
| `03-04` | Cloud connector, manifest | `04_manifest.yml` |
| `05-06` | Content credentials, products | `06a_products.yml` |
| `07-08` | Sync plans, lifecycle environments | `08_lifecycle_environments.yml` |
| `09-10` | Domains, subnets | `10_subnets.yml` |
| `11` | Content views (regular, composite, rolling) | `11b_content_views.yml` |
| `12` | Satellite settings (split by area) | `12c_settings_remote_execution.yml` |
| `13` | Operating systems | `13_operating_systems.yml` |
| `14` | Activation keys | `14_activation_keys.yml` |
| `15` | Host groups (layered hierarchy) | `15a_host_groups_base.yml` |
| `16` | Global parameters | `16b_global_parameters_remote_execution.yml` |
| `17` | OpenSCAP compliance | `17_openscap.yml` |
| `18-19` | Roles, users | `18_roles.yml` |

### Merge Files

Several variable groups are split across multiple files for readability and
then merged in a dedicated file:

- `06c_combined_products.yml` merges `06a` (Red Hat) + `06b` (custom)
- `11e_combined_content_views.yml` merges `11a` through `11d`
- `12g_merge_settings.yml` merges `12a` through `12f`
- `15d_host_groups_merged.yml` merges `15a` through `15c`
- `16d_merge_global_parameters.yml` merges `16a` through `16c`

The playbooks consume only the merged variable (e.g. `satellite_products`,
`satellite_content_views`, `satellite_settings`, `satellite_hostgroups`,
`satellite_global_parameters`).

## Making Changes

### Adding a New Repository

1. Add the product and repository set to `06a_products.yml`
2. Run `06_satellite_products_and_repositories.yml` to enable it
3. Run `07_satellite_sync_repositories.yml` to synchronize

### Adding a Content View

1. Add the content view definition to `11b_content_views.yml` (or `11a` for
   custom products)
2. If composite, add to `11c_composite_content_views.yml`
3. Run `12_satellite_content_views.yml` to create it
4. Run `13_satellite_content_view_publish.yml` to publish and promote

### Adding a New RHEL Version

This requires changes across multiple files:

1. **Products** (`06a`): Add BaseOS, AppStream, Kickstart, and Satellite
   Client repositories for the new version
2. **Content views** (`11b`): Create a base content view with the new
   repositories
3. **Composite content views** (`11c`): Create a composite content view
   referencing the base CV
4. **Operating systems** (`13`): Add the OS definition
5. **Activation keys** (`14`): Create dev and prod activation keys
6. **Host groups** (`15a-15c`): Add OS-level and lifecycle-environment-level
   host groups
7. **OpenSCAP** (`17`): Add compliance policies for the new version

Then run the playbooks from step 06 onward, or use `site.yml`.

### Changing Satellite Settings

1. Edit the appropriate `12x_settings_*.yml` file
2. Run `14_satellite_settings.yml`

### Updating Secrets

All sensitive values are vault-encrypted in `00a_secrets.yml`. To edit:

```bash
ansible-vault edit host_vars/lab-satellite-6.crazy.lab/00a_secrets.yml
```

Or encrypt a new value:

```bash
ansible-vault encrypt_string 'my-secret-value' --name 'variable_name'
```

The `vault-pki.sh` helper script can vault-encrypt certificate files from
the `.pki/` directory for inclusion in `00a_secrets.yml`.

### Adding a Capsule

1. Add the Capsule host to `inventory` under a `[capsule]` group
2. Create `host_vars/<capsule-fqdn>/` with the required variable files
   (certificates, firewall rules, installer configuration)
3. On the Satellite server, generate the Capsule certificate archive:
   ```bash
   capsule-certs-generate --foreman-proxy-fqdn <capsule-fqdn> \
     --certs-tar /root/<capsule-fqdn>-certs.tar
   ```
4. Run the Capsule installer playbook:
   ```bash
   ansible-playbook 02_capsule_installer.yml --limit <capsule-fqdn>
   ```

## Host Group Hierarchy

Host groups follow a layered structure for maximum reusability:

```
hg-base                              # Architecture, Ansible roles
├── hg-rhel-8                        # OS, PXE loader, partition table
│   ├── hg-ansible_automation_platform-rhel-8
│   │   ├── ...-dev                  # Lifecycle env, content view, activation key
│   │   └── ...-prod
│   └── hg-default-rhel-8
│       ├── ...-dev
│       └── ...-prod
├── hg-rhel-9
│   └── (same pattern)
└── hg-rhel-10
    └── (same pattern)
```

## Running on Ansible Automation Platform (AAP)

This project is designed to run on AAP without modification:

1. **Project**: Point to this Git repository
2. **Credentials**:
   - **Vault credential**: Provide the vault password
   - **Machine credential**: SSH access to the Satellite host (`cloud-user`)
3. **Job Templates**: Create one per playbook, or a Workflow Template that
   chains them in order (mirroring `site.yml`)

Secrets (RHSM credentials, SSH keys, certificates) are vault-encrypted in
the repository and travel with the project -- no external secret store is
required.

## License

MIT
