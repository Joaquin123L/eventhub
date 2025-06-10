
from datetime import timedelta

from django.test import TestCase
from django.utils.timezone import now

from app.models import Event, Favorite, User


class ToggleFavoriteViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.organizer = User.objects.create_user(username='organizer', password='password')
        self.event = Event.objects.create(
            title='Concierto',
            description='Concierto de rock',
            scheduled_at=now() + timedelta(days=3),
            organizer=self.organizer
        )

    def test_create_favorite_successfully(self):
        favorite = Favorite.objects.create(user=self.user, event=self.event)
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.event, self.event)
        self.assertEqual(Favorite.objects.count(), 1)

    def test_duplicate_favorite(self):
        Favorite.objects.create(user=self.user, event=self.event)
        with self.assertRaises(Exception):
            Favorite.objects.create(user=self.user, event=self.event)
