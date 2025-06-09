import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, Rating, Ticket, User


class OrganizerRatingVisibilityTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizador@example.com",
            password="pass",
            is_organizer=True
        )

        self.user1 = User.objects.create_user(
            username="user1", email="email@example.com", password="pass", is_organizer=False
        )
        self.user2 = User.objects.create_user(
            username="user2", email="email2@example.com", password="pass", is_organizer=False
        )

        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
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

    def test_organizer_sees_average_rating(self):
        self.client.login(username="organizer", password="pass")
        url = reverse("event_detail", args=[self.event.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("promedio_rating", response.context)

        expected_avg = (3 + 5) / 2
        self.assertAlmostEqual(response.context["promedio_rating"], expected_avg, places=2)
