import sys
from time import sleep

import pygame

import screen_background as sb
from alien import Alien
from bullet import Bullet
from button import Button
from game_stats import GameStats
from scoreboard import Scoreboard
from settings import Settings
from ship import Ship


class AlienInvasion:

    def __init__(self):
        pygame.init()

        self.settings = Settings()
        if self.settings.full_screen:
            self.screen = pygame.display.set_mode((self.settings.screen_width,
                                                   self.settings.screen_height),
                                                  pygame.FULLSCREEN)
            self.settings.screen_width = self.screen.get_rect().width
            self.settings.screen_height = self.screen.get_rect().height
        else:
            self.screen = pygame.display.set_mode((self.settings.screen_width,
                                                   self.settings.screen_height))

        pygame.display.set_caption("Alien Invasion")

        self.background = sb.ScreenBackground(self)
        self.stats = GameStats(self)
        self.scoreboard = Scoreboard(self)

        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()
        self._create_fleet()
        self.play_button = Button(self, "Play")

        # Play bg music
        pygame.mixer.music.load('sound/background.mp3')
        pygame.mixer.music.play(-1, 0.0)
        # pygame.mixer.music.stop()

        # Load effect sounds
        self.sound_shot = pygame.mixer.Sound('sound/shot.wav')
        self.sound_explosion = pygame.mixer.Sound('sound/explosion.wav')
        self.sound_explosion_ship = pygame.mixer.Sound('sound/explosion_ship.wav')

    def run_game(self):
        self._init_time()

        while True:
            # Calculate delta time
            ticks = pygame.time.get_ticks()
            self.settings.delta_time = (ticks - self.last_ticks) * 0.001
            # Max 100Fps
            if self.settings.delta_time < 0.01:
                continue
            # Update last_ticks
            self.last_ticks = ticks

            self._check_events()
            if self.stats.game_active:
                self.background.update()
                self.ship.update()
                self._update_aliens()
                self._update_bullets()

            self._update_screen()

    def _init_time(self):
        self.last_ticks = pygame.time.get_ticks()

    def _update_aliens(self):
        self._check_fleet_edges()
        self.aliens.update()

        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

        self._check_aliens_bottom()

    def _check_bullet_alien_collisions(self):
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)

        if collisions:
            for aliens in collisions.values():
                self.sound_explosion.play()
                self.stats.score += self.settings.alien_points * len(aliens)

            self.scoreboard.prep_score()
            self.scoreboard.check_high_score()

        if not self.aliens:
            self.bullets.empty()
            self._create_fleet()
            self.settings.increase_speed()

            self.stats.level += 1
            self.scoreboard.prep_level()

    def _check_aliens_bottom(self):
        screen_rect = self.screen.get_rect()
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= screen_rect.bottom:
                self._ship_hit()
                break

    def _update_bullets(self):
        self.bullets.update()

        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _create_fleet(self):
        alien = Alien(self)
        alian_width, alien_height = alien.rect.size
        available_space_x = self.settings.screen_width - (2 * alian_width)
        number_aliens_x = available_space_x // (2 * alian_width)

        ship_height = self.ship.rect.height
        available_space_y = self.settings.screen_height - (3 * alien_height) - ship_height
        number_rows = available_space_y // (2 * alien_height)

        for row_number in range(number_rows):
            for alien_number in range(number_aliens_x):
                self._create_alien(alien_number, row_number)

    def _create_alien(self, alien_number, row_number):
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size
        alien.x = alien_width + 2 * alien_width * alien_number
        alien.rect.x = alien.x
        alien.rect.y = alien_height + 2 * alien_height * row_number
        self.aliens.add(alien)

    def _show_ship_explosion(self):
        # Show ship explosion
        self.ship.show_explosion_ship_img()
        self._update_screen()
        # Show standard ship image
        self.ship.show_ship_img()

    def _ship_hit(self):
        self._show_ship_explosion()
        self.sound_explosion_ship.play()

        if self.stats.ships_left > 0:
            self.stats.ships_left -= 1
            self.scoreboard.prep_ships()

            self.aliens.empty()
            self.bullets.empty()

            self._create_fleet()
            self.ship.center_ship()

            # TODO use timer!!!
            sleep(1.5)

            self._init_time()
        else:
            self.stats.game_active = False

    def _check_fleet_edges(self):
        alien: Alien
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        for alien in self.aliens.sprites():
            alien.rect.y += self.settings.fleet_drop_speed

        self.settings.fleet_direction *= -1

    def _check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_play_button(mouse_pos)

    def _check_play_button(self, mouse_pos):
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        if button_clicked and not self.stats.game_active:
            self.settings.initialize_dynamic_settings()
            self.stats.reset_stats()
            self.stats.game_active = True

            self.scoreboard.prep_score()
            self.scoreboard.prep_level()
            self.scoreboard.prep_ships()

            self.aliens.empty()
            self.bullets.empty()

            self._create_fleet()
            self.ship.center_ship()

    def _check_keydown_events(self, event):
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = True
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = True
        elif event.key == pygame.K_SPACE:
            self._fire_bullet()
        elif event.key == pygame.K_ESCAPE:
            sys.exit()

    def _fire_bullet(self):
        if len(self.bullets) < self.settings.bullets_allowed:
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)
            self.sound_shot.play()

    def _check_keyup_events(self, event):
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = False
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = False

    def _update_screen(self):
        self.background.blitme()

        self.ship.blitme()
        self.aliens.draw(self.screen)
        self.scoreboard.show_score()

        bullet: Bullet
        for bullet in self.bullets.sprites():
            bullet.draw_bullet()

        if not self.stats.game_active:
            self.play_button.draw_button()

        pygame.display.flip()


if __name__ == '__main__':
    ai = AlienInvasion()
    ai.run_game()
