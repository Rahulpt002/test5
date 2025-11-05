from django.core.management.base import BaseCommand

from purchases.models import Course


class Command(BaseCommand):
    help = "Seed the database with additional demo courses"

    def handle(self, *args, **options):
        courses = [
            ("JavaScript Essentials", "Master JS fundamentals.", 79900),
            ("React for Beginners", "Build UIs with React.", 109900),
            ("Advanced React", "Hooks, context, performance.", 129900),
            ("Node.js API Development", "Build REST APIs.", 99900),
            ("Full-Stack Django", "End-to-end Django apps.", 119900),
            ("Data Structures in Python", "DS and algorithms.", 89900),
            ("Algorithms Mastery", "Problem solving patterns.", 99900),
            ("SQL & Databases", "Relational DB basics.", 69900),
            ("PostgreSQL Deep Dive", "Indexes, queries, tuning.", 99900),
            ("Git & GitHub", "Version control workflow.", 49900),
            ("Docker Basics", "Containerize your apps.", 79900),
            ("Kubernetes Intro", "Orchestrate containers.", 129900),
            ("Linux for Devs", "CLI skills for developers.", 59900),
            ("AWS Foundations", "Core AWS services.", 119900),
            ("GCP Foundations", "Core GCP services.", 119900),
            ("Azure Foundations", "Core Azure services.", 119900),
            ("REST API Design", "Best practices & patterns.", 89900),
            ("Testing in Django", "Unit, integration, pytest.", 79900),
            ("Async Python", "asyncio, aiohttp basics.", 99900),
            ("System Design Basics", "Scale and reliability.", 139900),
        ]

        created_count = 0
        for title, desc, price in courses:
            obj, created = Course.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "price_in_paise": price,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} new courses."))


