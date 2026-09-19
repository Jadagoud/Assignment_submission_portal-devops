import os
from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.assignment import Assignment
from app.models.group import Group, GroupMember
from app.models.submission import Submission
from app.models.audit_log import AuditLog
from app.services.cache_service import CacheService

app = create_app(os.getenv("FLASK_ENV", "development"))


def seed_database():
    with app.app_context():
        print("🌱 Seeding database for Assignment Group Portal...")
        db.create_all()

        # Check if already seeded
        if User.query.filter_by(email="admin@gmail.com").first():
            print("Database already contains seed data. Exiting.")
            return

        # 1. Create Administrator
        admin = User(
            full_name="Prof. Sarah Jenkins",
            email="admin@gmail.com",
            role=User.ROLE_ADMIN,
            bio="Lead Distributed Systems Instructor & Cloud Architecture Evaluator.",
        )
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.flush()

        # 2. Create Students
        students_data = [
            ("Alex Mercer", "alex@portal.edu", "CS-2026-101", "Backend specialist & Python enthusiast"),
            ("Beatrice Vance", "beatrice@portal.edu", "CS-2026-102", "Cloud infrastructure & Terraform nerd"),
            ("Charles Xavier", "charles@portal.edu", "CS-2026-103", "Full stack engineer & DevOps learner"),
            ("David Kim", "david@portal.edu", "CS-2026-104", "Database optimization & Redis caching fan"),
            ("Elena Rostova", "elena@portal.edu", "CS-2026-105", "Site reliability & Kubernetes administrator"),
        ]

        student_objs = []
        for name, email, sid, bio in students_data:
            stu = User(
                full_name=name,
                email=email,
                student_id=sid,
                role=User.ROLE_STUDENT,
                bio=bio,
            )
            stu.set_password("Student@12345")
            db.session.add(stu)
            student_objs.append(stu)

        db.session.flush()

        # 3. Create Assignments
        now = datetime.now(timezone.utc)

        # Assignment 1: Example from Prompt -> "Create AWS VPC", Group Size: 3
        a1 = Assignment(
            title="Create AWS VPC Architecture",
            description=(
                "Architect and deploy a high-availability AWS Virtual Private Cloud (VPC) spanning 2 Availability Zones. "
                "Deliverables must include Public & Private subnets, NAT Gateways, Internet Gateway, Security Groups, "
                "and Network Access Control Lists (NACLs) configured with least-privilege egress controls."
            ),
            assignment_type=Assignment.TYPE_GROUP,
            max_group_size=3,
            max_groups=1,
            status=Assignment.STATUS_OPEN,
            due_date=now + timedelta(days=14),
            created_by_id=admin.id,
        )

        # Assignment 2: Distributed Cache (Group size 2, will be FULL and SUBMITTED)
        a2 = Assignment(
            title="Distributed Caching Layer using Redis",
            description=(
                "Build a resilient caching tier around a relational PostgreSQL data store using Redis. Implement "
                "Write-Through and Cache-Aside invalidation strategies, handling cache stampede and serialization benchmarks."
            ),
            assignment_type=Assignment.TYPE_GROUP,
            max_group_size=2,
            max_groups=1,
            status=Assignment.STATUS_FULL,
            due_date=now + timedelta(days=7),
            created_by_id=admin.id,
        )

        # Assignment 3: Kubernetes Microservices (Group size 4, OPEN)
        a3 = Assignment(
            title="Containerized Microservices Cluster",
            description=(
                "Deploy a multi-service polyglot architecture on Kubernetes with automated health checks, "
                "Horizontal Pod Autoscalers (HPA), Ingress controllers, and persistent volume claims."
            ),
            assignment_type=Assignment.TYPE_GROUP,
            max_group_size=4,
            max_groups=2,
            status=Assignment.STATUS_OPEN,
            due_date=now + timedelta(days=21),
            created_by_id=admin.id,
        )

        # Assignment 4: Individual Assignment
        a4 = Assignment(
            title="Database Normalization & Query Tuning",
            description=(
                "Analyze and normalize an unindexed 10-million row e-commerce schema to BCNF. Provide EXPLAIN ANALYZE "
                "execution plans demonstrating index optimization and partitioned table query performance."
            ),
            assignment_type=Assignment.TYPE_INDIVIDUAL,
            max_group_size=1,
            max_groups=5,
            status=Assignment.STATUS_OPEN,
            due_date=now + timedelta(days=10),
            created_by_id=admin.id,
        )

        # Assignment 5: Closed Assignment
        a5 = Assignment(
            title="Legacy Monolith Static Code Analysis",
            description="Semester intro diagnostic assignment. Audit and refactor a legacy Python codebase.",
            assignment_type=Assignment.TYPE_INDIVIDUAL,
            max_group_size=1,
            max_groups=10,
            status=Assignment.STATUS_CLOSED,
            due_date=now - timedelta(days=3),
            created_by_id=admin.id,
        )

        db.session.add_all([a1, a2, a3, a4, a5])
        db.session.flush()

        # 4. Form Groups and Memberships
        # On Assignment 1 (AWS VPC, size 3): Alex & Beatrice have joined (2/3). 1 spot remains before auto-locking!
        g1 = Group(
            assignment_id=a1.id,
            group_number=1,
            name=f"Team 1 - {a1.title}",
            is_full=False,
            status=Group.STATUS_FORMING,
        )
        db.session.add(g1)
        db.session.flush()

        m1 = GroupMember(group_id=g1.id, user_id=student_objs[0].id, assignment_id=a1.id)
        m2 = GroupMember(group_id=g1.id, user_id=student_objs[1].id, assignment_id=a1.id)
        db.session.add_all([m1, m2])

        # On Assignment 2 (Distributed Cache, size 2): Charles & David joined (2/2) -> Group is FULL! Assignment is FULL!
        g2 = Group(
            assignment_id=a2.id,
            group_number=1,
            name=f"Team 1 - {a2.title}",
            is_full=True,
            status=Group.STATUS_SUBMITTED,
        )
        db.session.add(g2)
        db.session.flush()

        m3 = GroupMember(group_id=g2.id, user_id=student_objs[2].id, assignment_id=a2.id)
        m4 = GroupMember(group_id=g2.id, user_id=student_objs[3].id, assignment_id=a2.id)
        db.session.add_all([m3, m4])

        # Submission for Group 2
        sub1 = Submission(
            assignment_id=a2.id,
            group_id=g2.id,
            submitted_by_id=student_objs[2].id,
            repo_url="https://github.com/charles-xavier/redis-cache-tier",
            docs_url="https://notion.so/redis-distributed-cache-architecture-spec",
            remarks="Completed cache invalidation decorators, Redis Sentinel connection pool, and JMeter load test results.",
            status=Submission.STATUS_PENDING,
        )
        db.session.add(sub1)

        # Audit logs
        AuditLog.log("DATABASE_INITIALIZED", "system", 0, "System seed data loaded with sample teams.")

        db.session.commit()
        CacheService.invalidate_all_assignment_caches()
        print("✅ Database seeding completed successfully!")
        print("--------------------------------------------------")
        print("Credentials for testing:")
        print("Admin:   admin@gmail.com    / Admin@12345")
        print("Student: alex@portal.edu     / Student@12345 (in Team 1, waiting for 1 more!)")
        print("Student: elena@portal.edu    / Student@12345 (ready to join Team 1 & trigger FULL lock!)")
        print("--------------------------------------------------")


if __name__ == "__main__":
    seed_database()
