from app.models import User, Event, Rating, Ticket
from app.test.test_e2e.base import BaseE2ETest
from django.utils import timezone
import datetime


class VerPromedioRatingE2ETest(BaseE2ETest):
    def setUp(self):
        super().setUp()

        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizador@example.com",
            password="pass123",
            is_organizer=True,
        )

        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass123",
            is_organizer=False,
        )

        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123",
            is_organizer=False,
        )

        self.event = Event.objects.create(
            title="Evento E2E",
            description="Evento con ratings",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        Ticket.objects.create(
            buy_date="2025-05-20", user=self.user1, event=self.event,
            ticket_code="CODE1", quantity="1", type="general"
        )

        Ticket.objects.create(
            buy_date="2025-05-20", user=self.user2, event=self.event,
            ticket_code="CODE2", quantity="1", type="general"
        )

        Rating.objects.create(user=self.user1, event=self.event, rating=3)
        Rating.objects.create(user=self.user2, event=self.event, rating=5)

    def test_organizer_ve_promedio_rating(self):
        self.login_user("organizer", "pass123")

        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}")

        rating_block = self.page.locator(".rating.text-warning.mt-2")
        rating_block.wait_for(timeout=5000)

        percentage_span = rating_block.locator("span.ms-2")
        percentage_text = percentage_span.inner_text()
        print("Texto de porcentaje:", percentage_text)
        
        expected_avg = (3 + 5) / 2  
        expected_percentage = round((expected_avg / 5) * 100, 1) 

        expected_text = f"({str(expected_percentage).replace('.', ',')}%)"  

        assert expected_text in percentage_text, f"Se esperaba ver {expected_text}, pero se encontró {percentage_text}"


