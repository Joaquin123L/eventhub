from app.test.test_e2e.base import BaseE2ETest
from app.models import User, Event, Favorite
from django.utils import timezone
import datetime


class EventFavoritesE2ETest(BaseE2ETest):
    def setUp(self):
        super().setUp()

        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="pass123",
            is_organizer=True,
        )

        self.user = User.objects.create_user(
            username="attendee",
            email="attendee@example.com",
            password="pass123",
            is_organizer=False,
        )

        self.event = Event.objects.create(
            title="Public Event",
            description="Visible to attendees",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

    def test_user_can_mark_event_as_favorite_from_list(self):
        '''Verifica que un usuario puede marcar un evento como favorito desde la lista de eventos'''
        self.login_user("attendee", "pass123")

        self.page.goto(f"{self.live_server_url}/events/")
        favorite_button = self.page.locator(f"a.favorite-btn[data-event-id='{self.event.id}']")
        favorite_button.wait_for(timeout=3000)

        favorite_button.click()

        self.page.wait_for_timeout(500)
        updated_button = self.page.locator(f"a.favorite-btn.btn-danger[data-event-id='{self.event.id}']")
        assert updated_button.is_visible(), "Event should appear as favorite (btn-danger not found)"

    def test_user_can_unmark_event_as_favorite_from_list(self):
        '''Verifica que un usuario puede quitar un evento de sus favoritos desde la lista'''
        self.login_user("attendee", "pass123")

        self.page.goto(f"{self.live_server_url}/events/")
        favorite_button = self.page.locator(f"a.favorite-btn[data-event-id='{self.event.id}']")
        favorite_button.click()
        self.page.wait_for_timeout(500)

        updated_button = self.page.locator(f"a.favorite-btn.btn-danger[data-event-id='{self.event.id}']")
        updated_button.click()
        self.page.wait_for_timeout(500)

        unmarked_button = self.page.locator(f"a.favorite-btn.btn-outline-danger[data-event-id='{self.event.id}']")
        assert unmarked_button.is_visible(), "Event should be unfavorited (btn-outline-danger not visible)"

    def test_favorite_button_state_persists_after_reload(self):
        '''Verifica que el estado de favorito se mantiene después de recargar la página'''
        self.login_user("attendee", "pass123")

        self.page.goto(f"{self.live_server_url}/events/")
        self.page.locator(f"a.favorite-btn[data-event-id='{self.event.id}']").click()
        self.page.wait_for_timeout(300)

        self.page.reload()
        updated_button = self.page.locator(f"a.favorite-btn.btn-danger[data-event-id='{self.event.id}']")
        assert updated_button.is_visible(), "Favorite state should persist after reload"

    def test_only_non_organizers_see_favorite_button(self):
        '''Verifica que solo los usuarios no organizadores pueden ver el botón para agregar a favoritos'''
        self.login_user("organizer", "pass123")
        self.page.goto(f"{self.live_server_url}/events/")

        favorite_btn = self.page.locator(f"a.favorite-btn[data-event-id='{self.event.id}']")
        assert not favorite_btn.is_visible(), "Organizer should not see the favorite button"


class EventFavoritesFilterE2ETest(BaseE2ETest):
    def setUp(self):
        super().setUp()

        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="pass123",
            is_organizer=True,
        )

        self.user = User.objects.create_user(
            username="attendee",
            email="attendee@example.com",
            password="pass123",
            is_organizer=False,
        )

        self.event1 = Event.objects.create(
            title="Favorito",
            description="Evento marcado como favorito",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        self.event2 = Event.objects.create(
            title="No Favorito",
            description="Evento que no es favorito",
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
        )

        Favorite.objects.create(user=self.user, event=self.event1)

    def test_favorites_only_checkbox_visible_for_non_organizer(self):
        '''Verifica que el checkbox "Solo favoritos" se muestra a usuarios que no son organizadores'''
        self.login_user("attendee", "pass123")
        self.page.goto(f"{self.live_server_url}/events/")
        checkbox = self.page.locator("input#favorites_only")
        assert checkbox.is_visible(), "The 'Favorites only' checkbox should be visible to attendees"

    def test_favorites_only_checkbox_not_visible_for_organizer(self):
        '''Verifica que los organizadores no pueden ver el checkbox Solo favoritos'''
        self.login_user("organizer", "pass123")
        self.page.goto(f"{self.live_server_url}/events/")
        checkbox = self.page.locator("input#favorites_only")
        assert not checkbox.is_visible(), "Organizers should not see the 'Favorites only' checkbox"

    def test_filter_shows_only_favorites_when_checked(self):
        '''Verifica que al marcar el checkbox, solo se muestran los eventos marcados como favoritos'''
        self.login_user("attendee", "pass123")
        self.page.goto(f"{self.live_server_url}/events/")
        self.page.check("input#favorites_only")
        self.page.wait_for_timeout(1000)

        event_rows = self.page.locator("table tbody tr")
        assert event_rows.count() == 1, "Only favorite events should be visible"
        assert "Favorito" in event_rows.nth(0).inner_text()

    def test_filter_resets_when_unchecked(self):
        '''Verifica que al desmarcar el checkbox, se vuelven a mostrar todos los eventos'''
        self.login_user("attendee", "pass123")
        self.page.goto(f"{self.live_server_url}/events/")
        self.page.check("input#favorites_only")
        self.page.wait_for_timeout(300)
        self.page.uncheck("input#favorites_only")
        self.page.wait_for_timeout(1000)

        event_rows = self.page.locator("table tbody tr")
        assert event_rows.count() == 2, "All events should be visible after unchecking the filter"
