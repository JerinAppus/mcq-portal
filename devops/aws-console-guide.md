# MCQ Battle Platform: Manual AWS Console Setup Guide

This guide provides step-by-step instructions to manually configure a custom VPC, Public/Private Subnets, Security Groups, an RDS MySQL Database, and an Application Load Balancer (ALB) directly inside the AWS Management Console. 

This manual approach is ideal for project demonstrations and evaluator reviews.

---

## Part 1: Create a Custom VPC & Subnets

### Step 1.1: Create the VPC
1. Log into your **AWS Management Console** and navigate to the **VPC Dashboard**.
2. Click **Create VPC** in the top right.
3. Configure the following:
   - **Resources to create**: Select **VPC only**.
   - **Name tag**: `mcq-custom-vpc`
   - **IPv4 CIDR block**: `10.0.0.0/16`
4. Click **Create VPC** at the bottom.

### Step 1.2: Create Subnets (2 Public, 2 Private)
Navigate to **Subnets** in the left sidebar and click **Create subnet**.
1. Select your VPC: `mcq-custom-vpc`.
2. Configure **Subnet 1 (Public AZ-A)**:
   - **Subnet name**: `mcq-public-subnet-1`
   - **Availability Zone**: Select your region's `a` zone (e.g., `ap-south-1a`).
   - **IPv4 CIDR block**: `10.0.1.0/24`
3. Click **Add new subnet** to configure **Subnet 2 (Public AZ-B)**:
   - **Subnet name**: `mcq-public-subnet-2`
   - **Availability Zone**: Select your region's `b` zone (e.g., `ap-south-1b`).
   - **IPv4 CIDR block**: `10.0.2.0/24`
4. Click **Add new subnet** to configure **Subnet 3 (Private AZ-A)**:
   - **Subnet name**: `mcq-private-subnet-1`
   - **Availability Zone**: Select your region's `a` zone (e.g., `ap-south-1a`).
   - **IPv4 CIDR block**: `10.0.10.0/24`
5. Click **Add new subnet** to configure **Subnet 4 (Private AZ-B)**:
   - **Subnet name**: `mcq-private-subnet-2`
   - **Availability Zone**: Select your region's `b` zone (e.g., `ap-south-1b`).
   - **IPv4 CIDR block**: `10.0.20.0/24`
6. Click **Create subnet** at the bottom.

### Step 1.3: Enable Auto-assign Public IP for Public Subnets
1. Select `mcq-public-subnet-1` from the list.
2. Click **Actions** -> **Edit subnet settings**.
3. Check the box for **Enable auto-assign public IPv4 address**. Click **Save**.
4. Repeat this exact process for `mcq-public-subnet-2`.

---

## Part 2: Configure Routing & Internet Access

### Step 2.1: Create an Internet Gateway (IGW)
1. Navigate to **Internet gateways** in the left sidebar.
2. Click **Create internet gateway**.
3. Name it `mcq-igw` and click **Create internet gateway**.
4. Once created, click **Actions** -> **Attach to VPC**.
5. Select `mcq-custom-vpc` and click **Attach internet gateway**.

### Step 2.2: Configure Route Tables
1. Navigate to **Route tables** in the left sidebar.
2. Select the route table associated with your `mcq-custom-vpc` (you can rename it `mcq-public-rt`).
3. Click on the **Routes** tab at the bottom and click **Edit routes**.
4. Click **Add route**:
   - **Destination**: `0.0.0.0/0`
   - **Target**: Select **Internet Gateway** and click `mcq-igw`.
5. Click **Save changes**.
6. Click the **Subnet associations** tab at the bottom, then click **Edit subnet associations**.
7. Select **`mcq-public-subnet-1`** and **`mcq-public-subnet-2`** and click **Save associations**.

*Note: The private subnets (`mcq-private-subnet-1` & `mcq-private-subnet-2`) will automatically use the default main route table which has no route to the Internet Gateway, keeping them isolated.*

---

## Part 3: Create Security Groups (Least Privilege)

Navigate to the **EC2 Dashboard** -> **Security Groups** -> **Create security group**.

### Group 1: `mcq-alb-sg` (For the Load Balancer)
- **Description**: Allow public web access to ALB.
- **VPC**: Select `mcq-custom-vpc`.
- **Inbound Rules**:
  - Add Rule: **HTTP** (Port 80) from **Anywhere-IPv4** (`0.0.0.0/0`).
  - Add Rule: **HTTPS** (Port 443) from **Anywhere-IPv4** (`0.0.0.0/0`).
- Click **Create security group**.

### Group 2: `mcq-web-sg` (For your EC2 Instance)
- **Description**: Allow inbound traffic ONLY from ALB and SSH from your IP.
- **VPC**: Select `mcq-custom-vpc`.
- **Inbound Rules**:
  - Add Rule: **HTTP** (Port 80) -> Source select **Custom** -> Search and select **`mcq-alb-sg`**.
  - Add Rule: **HTTPS** (Port 443) -> Source select **Custom** -> Search and select **`mcq-alb-sg`**.
  - Add Rule: **SSH** (Port 22) -> Source select **My IP**.
- Click **Create security group**.

### Group 3: `mcq-db-sg` (For your RDS MySQL Database)
- **Description**: Allow database connections ONLY from EC2.
- **VPC**: Select `mcq-custom-vpc`.
- **Inbound Rules**:
  - Add Rule: **MYSQL/Aurora** (Port 3306) -> Source select **Custom** -> Search and select **`mcq-web-sg`**.
- Click **Create security group**.

---

## Part 4: Launch RDS MySQL Database (Private Subnet)

### Step 4.1: Create a Subnet Group
1. Navigate to the **RDS Dashboard** -> **Subnet groups** on the left menu.
2. Click **Create DB subnet group**.
3. Configure:
   - **Name**: `mcq-db-subnet-group`
   - **VPC**: Select `mcq-custom-vpc`.
   - **Add subnets**: Select your region's availability zones (e.g., `ap-south-1a` and `ap-south-1b`).
   - Select the subnets matching your private CIDR blocks: **`10.0.10.0/24`** and **`10.0.20.0/24`**.
4. Click **Create**.

### Step 4.2: Create the MySQL Database
1. Navigate to **Databases** on the left menu and click **Create database**.
2. Configure:
   - **Choose a database creation method**: **Standard create**.
   - **Engine options**: **MySQL**.
   - **Templates**: Select **Free Tier** (Crucial to avoid charges).
   - **DB instance identifier**: `mcq-database`
   - **Credentials**: Set a username (e.g., `mcq_admin`) and a secure password.
   - **Instance configuration**: `db.t3.micro` or `db.t4g.micro`.
   - **Connectivity**:
     - **VPC**: `mcq-custom-vpc`.
     - **DB Subnet Group**: `mcq-db-subnet-group`.
     - **Public access**: Select **No** (Strict security).
     - **VPC security group**: Select **Choose existing** -> Select **`mcq-db-sg`** (and remove the `default` group).
   - **Additional configuration**:
     - **Initial database name**: `mcq_battle`.
3. Click **Create database** at the bottom.

---

## Part 5: Set Up Application Load Balancer

### Step 5.1: Create Target Group
1. Navigate to **EC2 Dashboard** -> **Target groups** on the left sidebar.
2. Click **Create target group**.
3. Configure:
   - **Target type**: **Instances**.
   - **Target group name**: `mcq-web-tg`.
   - **Port**: `80` (HTTP).
   - **VPC**: `mcq-custom-vpc`.
4. Click **Next** -> Click **Create target group** (We will register the EC2 instance later once launched).

### Step 5.2: Create Load Balancer
1. Navigate to **Load balancers** on the left sidebar.
2. Click **Create load balancer** -> Select **Application Load Balancer** -> Click **Create**.
3. Configure:
   - **Load balancer name**: `mcq-alb`.
   - **Scheme**: **Internet-facing**.
   - **Network mapping**:
     - **VPC**: `mcq-custom-vpc`.
     - **Mappings**: Check both availability zones and select **`mcq-public-subnet-1`** and **`mcq-public-subnet-2`**.
   - **Security groups**: Select **`mcq-alb-sg`** (remove `default`).
   - **Listeners and routing**:
     - **Protocol**: HTTP on Port 80.
     - **Default action**: Forward to **`mcq-web-tg`**.
4. Click **Create load balancer**.

Once created, copy the **DNS name** (e.g. `mcq-alb-xxxx.ap-south-1.elb.amazonaws.com`). Go to your domain registrar and create a **CNAME record** pointing `mcq-platform.duckdns.org` to this ALB DNS name.

---

## Part 6: Launch EC2 Instance & Connect RDS

1. Navigate to **EC2 Dashboard** -> **Instances** -> **Launch instances**.
2. Configure:
   - **Name**: `mcq-web-server`.
   - **AMI**: Ubuntu Server 22.04 LTS.
   - **Network settings**:
     - **VPC**: `mcq-custom-vpc`.
     - **Subnet**: Select **`mcq-public-subnet-1`**.
     - **Auto-assign public IP**: **Enable**.
     - **Security group**: Select **Select existing security group** -> **`mcq-web-sg`**.
   - **Key pair**: Select your `mcq-key`.
3. Click **Launch instance**.
4. Once launched, select the instance, click **Instance stats** -> **Register target** to add it to your Target Group `mcq-web-tg`.
5. SSH into the server, follow your Gunicorn/Nginx [deployment-guide.md](file:///c:/Desktop/mcq-portal/devops/deployment-guide.md), and set your database connection to point to your RDS MySQL Endpoint address!
