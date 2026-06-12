# AWS Graviton (Arm64) EC2 Setup Guide

This guide provides step-by-step instructions to launch a free-tier/trial eligible AWS Graviton (Arm64) EC2 instance running Ubuntu, and verify its architecture once connected.

---

## Step 1: Launching the AWS Graviton EC2 Instance

1. **Log in to the AWS Management Console**:
   Go to [https://aws.amazon.com/console/](https://aws.amazon.com/console/) and sign in to your AWS account.

2. **Navigate to the EC2 Dashboard**:
   In the search bar at the top, type **EC2** and select **EC2** from the services list.

3. **Launch Instance**:
   Click the orange **Launch instance** button.

4. **Name and Tags**:
   - Give your instance a name, for example: `arm64-llm-hackathon`.

5. **Choose an Amazon Machine Image (AMI)**:
   - Select **Ubuntu** (typically the default Ubuntu Server LTS).
   - Under **Architecture**, change the selection from **x86_64** to **64-bit (Arm)**.
   - *Example AMI*: `Ubuntu Server 24.04 LTS (HVM), SSD Volume Type` (with `Arm` architecture selected).

6. **Choose an Instance Type**:
   - In the **Instance type** dropdown, look for the Graviton family (e.g., `t4g` instances).
   - **t4g.small** (2 vCPUs, 2 GiB RAM) is often eligible for a free trial promotion depending on when you registered.
   - **t4g.medium** (2 vCPUs, 4 GiB RAM) is recommended if you wish to run `Phi-3-mini` (3.8B parameters) comfortably without running out of memory.
   - Choose the appropriate instance type based on your budget/trial eligibility.

7. **Key Pair (Login)**:
   - Select an existing key pair or click **Create new key pair**.
   - If creating a new one:
     - Key pair name: `arm64-key`
     - Key pair type: `RSA` or `ED25519`
     - Private key file format: `.pem` (for OpenSSH/Mac/Linux) or `.ppk` (for PuTTY on Windows).
     - Save the private key file safely on your local machine.

8. **Network Settings**:
   - Under **Firewall (security groups)**, choose **Create security group**.
   - Check **Allow SSH traffic from** and select **My IP** for maximum security, or **Anywhere** (`0.0.0.0/0`) if you need access from dynamic networks.
   - *Note*: You do **not** need to open port `11434` (Ollama's default port) to the public web unless you specifically want remote external access, as we will interact with it locally or tunnel through SSH.

9. **Configure Storage**:
   - Expand the storage size to at least **20 GiB** (or up to **30 GiB** if staying within the free tier limits). This provides enough space for OS, dependencies, and multiple LLM GGUF model files.
   - Ensure the volume type is `gp3` (standard high-performance general-purpose SSD).

10. **Launch**:
    - Click **Launch instance** in the Summary panel on the right.
    - Click **View all instances** to watch your instance initialize. Once the state changes to `Running` and Status Check is `2/2 checks passed`, your instance is ready!

---

## Step 2: SSH Into the Instance

1. Locate the **Public IPv4 address** of your newly launched instance on the EC2 Instances page.
2. Open your local terminal, navigate to the folder containing your private key file, and secure the key file permissions:
   ```bash
   chmod 400 arm64-key.pem
   ```
3. Establish the SSH connection (replace `<YOUR_INSTANCE_IP>` with your instance's public IP address):
   ```bash
   ssh -i arm64-key.pem ubuntu@<YOUR_INSTANCE_IP>
   ```

---

## Step 3: Verifying the Arm64 Architecture

Once you have successfully logged into the instance via SSH, run the following terminal commands to verify that you are running on an Arm64 (aarch64) system:

### 1. Check Processor Architecture via `uname`
```bash
uname -m
```
*Expected Output:*
`aarch64` (This confirms the machine is running a 64-bit Arm processor).

### 2. Inspect CPU Details via `lscpu`
```bash
lscpu
```
*Expected Output Details:*
- **Architecture**: `aarch64`
- **Byte Order**: `Little Endian`
- **Vendor ID**: `ARM`
- **Model name**: `Neoverse-N1` (or similar Graviton family processor name)

### 3. Verify a System Binary is Compiled for Arm64
```bash
file /bin/bash
```
*Expected Output:*
`/bin/bash: ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV)...`
