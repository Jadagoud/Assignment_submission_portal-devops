# Assignment Submission Portal — AWS DevOps Project

## 1. Project Overview

This project demonstrates the deployment and automation of an Assignment Submission Portal using AWS cloud services and modern DevOps practices.

The application was containerized with Docker and deployed using Amazon ECS Fargate. The project includes container image management, networking, database, caching, secrets management, monitoring, alerting, CI/CD, health checks, rolling deployments, and automatic rollback.

The CI/CD pipeline uses GitHub Actions with GitHub OIDC federation, so long-lived AWS access keys are not stored in GitHub.

---

## 2. AWS Architecture

```text
                         INTERNET
                             |
                             v
                    +-----------------+
                    |      ALB        |
                    |   HTTP : 80     |
                    +--------+--------+
                             |
                             v
                 +----------------------+
                 | Frontend ECS Fargate |
                 | Private Subnet       |
                 | Nginx :80            |
                 +----------+-----------+
                            |
                     ECS Service Connect
                            |
                            v
                 +----------------------+
                 | Backend ECS Fargate  |
                 | Private Subnet       |
                 | Gunicorn :5000       |
                 +-----+-----------+----+
                       |           |
                       v           v
                +----------+   +-----------+
                |   RDS    |   | ElastiCache|
                |PostgreSQL|   |   Redis    |
                |   :5432  |   | TLS :6379  |
                +----------+   +-----------+

Private ECS
     |
     v
Private Route Table
     |
     v
NAT Gateway
     |
     v
Internet Gateway
     |
     v
Internet


3. CI/CD Architecture


Developer
    |
    v
GitHub
    |
    v
GitHub Actions
    |
    | GitHub OIDC
    v
AWS IAM Role
    |
    v
Docker Build
    |
    v
Amazon ECR
    |
    v
ECS Task Definition
    |
    v
ECS Fargate
    |
    v
Rolling Deployment
    |
    +---- Health Check ----> Healthy
    |
    +---- Failure ---------> Circuit Breaker
                                  |
                                  v
                              Rollback
4. AWS Services Used
Area	                       AWS Service
Compute	ECS                      Fargate
Container Registry	        Amazon ECR
Load Balancing	         Application Load Balancer
Database	          Amazon RDS PostgreSQL
Cache	                 Amazon ElastiCache Redis
Secrets	                  AWS Secrets Manager
Networking	                Amazon VPC
Internet	              Internet Gateway
Private outbound access	       NAT Gateway
Service discovery	   ECS Service Connect
Monitoring	             Amazon CloudWatch
Notifications	                Amazon SNS
Identity	                 AWS IAM
CI/CD	                       GitHub Actions
GitHub/AWS authentication	GitHub OIDC



5. VPC and Networking

VPC CIDR:

172.31.0.0/16
Public Subnets

Used for internet-facing resources and NAT Gateway.

172.31.32.0/20
172.31.0.0/20
Private Subnets

Used for ECS workloads and private AWS services.

172.31.48.0/20
172.31.64.0/20

ECS tasks do not have public IP addresses.

Internet Gateway

The Internet Gateway provides internet connectivity to the public subnets.

NAT Gateway

Private ECS tasks use the NAT Gateway for outbound internet access.

Example:

Private ECS
    |
Private Route Table
    |
0.0.0.0/0
    |
NAT Gateway
    |
Internet Gateway
    |
Internet

The NAT Gateway is chargeable and should be deleted when the lab is no longer required.

6. ECS Fargate

ECS Fargate is used as the container compute platform.

ECS Cluster
assignment-portal-cluster
Backend Service
assignment-backend-service

Backend:

Port: 5000
Runtime: Fargate
CPU: 512
Memory: 1024 MB
Frontend Service
assignment-frontend-service

Frontend:

Port: 80
Runtime: Fargate

Both services run in private subnets.

7. Docker

The application is containerized using Docker.

Backend

The backend image contains:

Python
Flask application
Gunicorn
PostgreSQL dependencies
Redis client
Database migration support

The backend container listens on:

5000
Frontend

The frontend uses Nginx.

Frontend container
       |
       v
Nginx :80
       |
       v
Service Connect
       |
       v
Backend :5000


8. Amazon ECR

Two ECR repositories are used:

assignment-backend
assignment-frontend

GitHub Actions builds Docker images and pushes them to ECR.

Images are tagged using the Git commit SHA.

Example:

assignment-backend:<git-sha>

Using Git SHA tags provides traceability between:

Git commit
     |
     v
Docker image
     |
     v
ECS task definition
     |
     v
Running application


9. Application Load Balancer

The Application Load Balancer is internet-facing.

ALB
Listener: HTTP :80

The ALB forwards traffic to the frontend ECS service.

Health check:

Path: /
Matcher: 200-399

The 200-399 matcher is used because the application's / endpoint can redirect users to the login page.

For example:

GET /
   |
   v
302 redirect
   |
   v
/auth/login

A 302 response is therefore considered healthy for this application.

10. ECS Service Connect

ECS Service Connect provides service-to-service communication between frontend and backend.

Frontend:

assignment-backend:5000

Backend:

Port 5000

Communication:

Frontend
    |
    v
assignment-backend:5000
    |
    v
Service Connect
    |
    v
Backend ECS task

The backend does not need a public IP.

11. RDS PostgreSQL

Amazon RDS PostgreSQL is used as the application database.

Configuration used in the lab:

Engine: PostgreSQL 16
Instance: db.t3.micro
Storage: 20 GB gp3
Public access: Disabled
Port: 5432

The database is private and is accessed by the backend ECS service.

Security group flow:

Backend SG
     |
     | TCP 5432
     v
RDS SG

The database is not exposed directly to the internet.

12. AWS Secrets Manager

Database credentials are stored in AWS Secrets Manager rather than hard-coded in the application.

assignment/rds/database-url


The ECS task execution role is granted permission to retrieve the required secret.


Secrets are not stored in:


GitHub

Dockerfile
Git repository
README

source code


Never commit actual secret values.

13. ElastiCache Redis


Amazon ElastiCache Redis is used for caching.


The Redis cluster is private.

Backend access:


Backend ECS
    |
    | TCP 6379
    v
ElastiCache Redis

TLS is required by the Redis Serverless configuration.

The application therefore uses:

rediss://

instead of:

redis://

This was an important troubleshooting lesson during the deployment.

14. CloudWatch

CloudWatch Logs are configured for both services.

Log groups:

/ecs/assignment-backend
/ecs/assignment-frontend

CloudWatch was used extensively during troubleshooting.

Examples:

aws logs tail /ecs/assignment-backend
aws logs tail /ecs/assignment-frontend


15. CloudWatch Alarms

The project includes alarms for:

ECS high CPU
ECS high memory
ALB 5XX errors
RDS high CPU
Redis command volume

Example:

ECS CPU > 80%
        |
        v
CloudWatch Alarm

        |

        v

SNS


16. SNS Notifications


An SNS topic is used for monitoring alerts.


assignment-monitoring-alerts

CloudWatch alarms can publish notifications to SNS.


Architecture:

CloudWatch

    |
    v
Alarm

    |
    v
SNS Topic

    |
    v

Subscription



17. IAM


IAM roles are used instead of embedding AWS access keys inside containers.

Important ECS roles include:


ECS Task Execution Role


Used by ECS for tasks such as:

Pulling images from ECR
Sending logs to CloudWatch
Retrieving Secrets Manager values
ECS Task Role


Used by the application/task when AWS API access is required.

GitHub Actions Role

GitHub Actions assumes an AWS IAM role using OIDC.

This avoids storing:

AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

as long-lived GitHub secrets.


18. GitHub OIDC

GitHub Actions authenticates to AWS using OpenID Connect.

Flow:

GitHub Actions
       |
       | OIDC token
       v
AWS STS
       |
       v
GitHubActionsAssignmentRole
       |
       v

AWS resources


Advantages:


No long-lived AWS access keys in GitHub
Temporary AWS credentials

IAM-controlled permissions

Repository-specific trust policy


The trust relationship is restricted to the intended GitHub repository.


19. GitHub Actions CI/CD


Backend deployment workflow:


.github/workflows/backend-deploy.yml


Pipeline:

Git push

   |
   v

GitHub Actions
   |
   v

Checkout
   |
   v

Configure AWS credentials using OIDC
   |
   v
Login to ECR

   |
   v
Docker build
   |
   v
Docker push
   |
   v
Render ECS task definition
   |
   v
Deploy ECS service
   |
   v
Wait for service stability

The workflow is triggered when backend-related files change.

20. Rolling Deployment

ECS is configured for rolling deployment.

Configuration:


Deployment strategy: ROLLING

Maximum percent: 200

Minimum healthy percent: 100


Conceptually:


Old Task
   |

   | remains healthy

   |

New Task starts
   |
Health check

   |
Healthy
   |

Traffic continues
   |

Old task replaced


This reduces service interruption during deployments.


21. Deployment Circuit Breaker


The ECS deployment circuit breaker is enabled with rollback.

Configuration:

Circuit breaker: enabled
Rollback: enabled

If a deployment repeatedly fails, ECS can mark the deployment as failed and return to the previous deployment.


22. Automatic Rollback Demo

A deliberate invalid image was used during testing:

assignment-backend:rollback-test-invalid

The image did not exist in ECR.

ECS reported:

CannotPullContainerError


The deployment failed.


The ECS deployment circuit breaker then rolled back to the previous healthy revision.


The final state was:


Previous revision

    |
    v

Running: 1
Desired: 1

Rollout: COMPLETED


The invalid revision became:


FAILED
Desired: 0

Running: 0


This demonstrated automatic rollback successfully.


23. Health Check Troubleshooting

During the health-check demonstration, the ALB initially reported:

Target.ResponseCodeMismatch

and later:

Target.Timeout

CloudWatch logs showed Nginx errors such as:

upstream prematurely closed connection

and:

502 Bad Gateway

Further investigation showed the backend container was failing during database seeding.

The backend attempted to insert an administrator account that already existed:

admin@gmail.com

PostgreSQL returned:

UniqueViolation

The application therefore did not start correctly, causing:


Frontend Nginx

      |
      v

Backend unavailable
      |

      v
502 / timeout

      |
      v

ALB unhealthy



24. Database Seed Idempotency Fix


The seed script was updated so it checks whether the administrator already exists before inserting it.


Concept:


if User.query.filter_by(email="admin@gmail.com").first():
    print("Database already contains seed data. Exiting.")

    return


This makes the seed operation safer when containers restart.


After the change:


Git push
   |

   v
GitHub Actions
   |
   v
Docker build
   |
   v
ECR
   |
   v
ECS revision 12
   |
   v
Health check
   |
   v
Healthy

Final verified state:


Backend ECS

Revision: 12

Desired: 1
Running: 1

Rollout: COMPLETED


ALB

Target: healthy


25. Security Group Design


The architecture uses security-group-based communication.

Conceptually:

Internet
   |
   | TCP 80
   v
ALB SG
   |
   | TCP 80
   v
Frontend SG
   |
   | Service Connect / backend communication
   v
Backend SG
   |
   +---- TCP 5432 ----> RDS SG
   |
   +---- TCP 6379 ----> Redis SG

Database and Redis access is restricted to the appropriate application security group.


26. Repository Structure

Important DevOps files include:

.
├── .github/
│   └── workflows/
│       └── backend-deploy.yml

│

├── backend/

├── frontend/
├── database/

├── docs/
│

├── ecs-task-definition.json
├── entrypoint.sh
├── seed.py
├── .gitignore

└── README.md


Temporary AWS CLI task-definition exports and local testing files should not be committed unless they are intentionally required as project documentation.


27. Deployment Flow
Application deployment

Developer changes code

        |

        v

Git commit
        |
        v
Git push
        |
        v
GitHub Actions
        |
        v
Docker build
        |
        v
ECR
        |
        v
ECS Task Definition
        |
        v
ECS Rolling Deployment
        |
        v
Health Check
        |
   +----+----+
   |         |
 Healthy   Failure
   |         |
   v         v
Complete   Circuit
           Breaker
              |
              v
           Rollback


28. Troubleshooting Lessons
CRLF issue


Windows line endings caused problems in the Linux container for the shell entrypoint.


Fix:


sed -i 's/\r$//' entrypoint.sh
ALB 302 response


The application redirects / to login.


The ALB matcher was therefore configured for:


200-399

Redis connection

Initial:

redis://


failed with the Redis Serverless configuration.


Using TLS:

rediss://


resolved the connectivity issue.

GitHub OIDC

The initial trust-policy subject format did not match the repository's OIDC subject format.

The trust policy was corrected to the repository-specific immutable subject.

IAM PassRole

The first ECS deployment failed because GitHub Actions did not have:

iam:PassRole

The permission was added only for the ECS task execution and task roles.

Database seed

The seed script attempted to insert an existing administrator.

The seed logic was made idempotent.

29. Cost Considerations

Several AWS services used in this lab can incur charges.

Important resources to clean up after practice:

NAT Gateway
RDS
ECS Fargate tasks
Application Load Balancer
ElastiCache Redis Serverless
ECR storage
CloudWatch usage
SNS usage where applicable

Always verify the AWS Billing/Cost Management console before and after a lab.

30. Production Improvements

This project is a hands-on DevOps learning implementation.

For production, consider:

HTTPS using ACM
Route 53 DNS
WAF
CloudFront where appropriate
Multi-AZ NAT Gateway strategy
RDS Multi-AZ
Automated database backups
Redis production sizing
Infrastructure as Code using Terraform
Separate development/staging/production environments
Automated tests before deployment
Blue/green deployments for suitable workloads
Centralized observability
Security scanning for Docker images
ECR image lifecycle policies
More restrictive IAM policies
Secrets rotation
GitHub environment approvals
Vulnerability scanning
Disaster recovery procedures

31. Important Security Rules

Never commit:

AWS access keys
AWS secret keys
Database passwords
Secrets Manager values
Private keys
GitHub tokens
Production credentials

Use:

IAM roles
GitHub OIDC
AWS Secrets Manager
Environment variables

instead.

32. Project Learning Outcomes

This project demonstrates practical knowledge of:

Linux
Docker
AWS networking
VPC
Security Groups
NAT Gateway
ECS
Fargate
ECR
ALB
Service Connect
RDS
Redis
Secrets Manager
CloudWatch
SNS
IAM
GitHub
GitHub Actions
OIDC
CI/CD
Rolling deployments
Health checks
Deployment rollback
Troubleshooting


33. Final Status

The following major components were successfully demonstrated:

Docker                         ✅
ECR                            ✅
ECS Fargate                    ✅
RDS PostgreSQL                 ✅
Secrets Manager                ✅
ALB                            ✅
Frontend ECS                   ✅
Service Connect                ✅
ElastiCache Redis              ✅
Private Subnets + NAT          ✅
CloudWatch                     ✅
SNS                            ✅
IAM                            ✅
GitHub OIDC                    ✅
GitHub Actions                 ✅
ECR → ECS deployment           ✅
Rolling deployment             ✅
Health checks                  ✅
Automatic rollback             ✅
CI/CD troubleshooting          ✅

The final verified backend deployment used ECS task definition revision 12 and the ALB frontend target was healthy.

34. Repository

GitHub repository:

Jadagoud/Assignment_submission_portal-devops

This repository contains the DevOps implementation and documentation for the Assignment Submission Portal project.
