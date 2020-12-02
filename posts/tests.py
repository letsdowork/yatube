import io
import tempfile

import mock

from django.core.files import File
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from posts.models import Comment, Follow, Group, Post, User


class BaseTest(TestCase):
    DUMMY_CACHE = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

    TEST_TEXT_1 = 'Lorem ipsum dolor sit amet'
    TEST_TEXT_2 = 'Proin consequat quam rutrum'
    TEST_TEXT_3 = 'Vivamus vel suscipit lorem. Ut id elit ex.'
    IMG_TAG = f'<img class="card-img" src="'

    def setUp(self):
        self.auth_user = User.objects.create(
            username='Obi-Wan', password='Kenobi', email='obi-wan@kenobi.com'
        )
        self.no_auth_user = User.objects.create(
            username='Dart', password='Weider', email='dart@weider.com'
        )
        self.auth_client = Client()
        self.no_auth_client = Client()
        self.auth_client.force_login(self.auth_user)
        self.group = Group.objects.create(
            title='AnyGroup', slug='any', description='For all themes'
        )

    def create_post(self, text, group, author):
        """Создать запись пользователя в базе данных."""
        post = Post.objects.create(text=text, group=group, author=author)
        self.post_id = post.id
        self.create_post_all_url_paths()

    def create_post_all_url_paths(self):
        """Создать стандартные пути страниц для проверок."""
        self.paths = {
            'index': {},
            'profile': {'username': self.auth_user.username},
            'post': {
                'username': self.auth_user.username,
                'post_id': self.post_id
            },
            'group': {'slug': self.group.slug}
        }


@override_settings(CACHES=BaseTest.DUMMY_CACHE)
class CacheNotRequiredTest(BaseTest):
    """Предоставляет запуск теста без кэширования данных."""
    pass


class PostTextTest(CacheNotRequiredTest):
    def test_profile_page_after_user_register(self):
        """После регистрации пользователя создается его персональная
        страница (profile)."""
        response = self.auth_client.get(
            reverse('profile', kwargs={'username': self.auth_user.username})
        )
        self.assertEqual(
            response.status_code, 200,
            msg='Не найдена страница профиля зарегестрированного пользователя'
        )

    def test_auth_user_can_publish_post(self):
        """Авторизованный пользователь может опубликовать пост (new)."""
        self.auth_client.post(reverse('new_post'), data={
            'text': self.TEST_TEXT_1,
            'group': self.group.pk
        })
        posts = Post.objects.filter(text=self.TEST_TEXT_1)
        self.assertNotEqual(
            posts.count(), 0,
            msg='Авторизованный пользователь не может оставить запись'
        )
        self.assertEqual(
            posts.count(), 1, msg=(
                'Запись пользователя должна создаваться в единственном '
                'экземпляре'
            )
        )
        post = Post.objects.all()[0]
        self.assertEqual(
            post.author, self.auth_user, msg='Не корректный автор записи'
        )
        self.assertEqual(
            post.group, self.group, msg='Не корректная группа записи'
        )
        self.assertEqual(
            post.text, self.TEST_TEXT_1, msg='Не корректный текст записи'
        )

    def test_no_auth_user_cant_publish_post(self):
        """Неавторизованный пользователь не может опубликовать пост (new)."""
        response = self.no_auth_client.post(reverse('new_post'), data={
            'text': self.TEST_TEXT_1,
            'group': self.group.pk
        })
        self.assertRedirects(
            response, '/auth/login/?next=/new/', status_code=302,
            target_status_code=200, msg_prefix='',
            fetch_redirect_response=True
        )

    def verify_post_contains_text(self, text):
        """Проверяем содержится ли искомый текст поста в контексте ответа."""
        for key in self.paths.keys():
            with self.subTest(key=key):
                response = self.auth_client.get(
                    reverse(key, kwargs=self.paths[key])
                )
                self.assertContains(
                    response, text, count=None, status_code=200,
                    msg_prefix=f'Текст записи не найден на странице {key}',
                    html=False,
                )
                post = response.context['post']
                self.assertEqual(
                    post.author, self.auth_user,
                    msg='Не соответствие автора поста'
                )
                self.assertEqual(
                    post.group, self.group,
                    msg='Не соответствие группы поста'
                )
                if key != 'post':
                    paginator = response.context['paginator']
                    self.assertEqual(
                        paginator.count, 1,
                        msg='Несоответствие количества записей'
                    )

    def verify_post_not_contains_text(self, text):
        """Проверка на отсутствие текста в контексте ответа."""
        for key in self.paths.keys():
            with self.subTest(key=key):
                response = self.auth_client.get(
                    reverse(key, kwargs=self.paths[key])
                )
                self.assertNotContains(
                    response, text, status_code=200,
                    msg_prefix=f'Найден текст записи на странице {key}',
                    html=False,
                )

    def test_post_availability_on_all_pages_after_publication(self):
        """После публикации поста новая запись появляется на главной странице
        сайта (index), на персональной странице пользователя (profile),
        и на отдельной странице поста (post)."""
        self.create_post(self.TEST_TEXT_1, self.group, self.auth_user)
        self.verify_post_contains_text(self.TEST_TEXT_1)

    def test_changing_a_post_on_all_pages_after_editing(self):
        """Авторизованный пользователь может отредактировать свой пост и его
        содержимое изменится на всех связанных страницах."""
        self.create_post(self.TEST_TEXT_1, self.group, self.auth_user)
        self.auth_client.post(reverse('post_edit', kwargs={
            'username': self.auth_user.username, 'post_id': self.post_id
        }), data={'text': self.TEST_TEXT_2, 'group': self.group.pk})
        self.verify_post_not_contains_text(self.TEST_TEXT_1)
        self.verify_post_contains_text(self.TEST_TEXT_2)

    def test_get_error404_when_page_not_found(self):
        """Выдать ошибку 404 если страница не найдена."""
        page = 'this_is_a_nonexistent_page'
        response = self.auth_client.get(page)
        self.assertEquals(response.status_code, 404)
        response = self.no_auth_client.get(page)
        self.assertEquals(response.status_code, 404)


class PostImageTest(CacheNotRequiredTest):
    def create_post_with_temporary_image(self):
        """Создать файл изображения во временной директории."""
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                byte_image = io.BytesIO()
                im = Image.new("RGB", size=(1000, 1000), color=(255, 0, 0, 0))
                im.save(byte_image, format='jpeg')
                byte_image.seek(0)
                image = ContentFile(byte_image.read(), name='test.jpeg')
                self.auth_client.post(
                    reverse('new_post'), data={
                        'text': self.TEST_TEXT_1,
                        'group': self.group.pk,
                        'author': self.auth_user,
                        'image': image
                    }
                )

    def test_tag_img_in_post_page(self):
        """Проверить, что страница поста содержит тэг <img>."""
        self.create_post_with_temporary_image()
        post = Post.objects.first()
        response = self.auth_client.get(reverse(
            'post', kwargs={
                'username': self.auth_user.username,
                'post_id': post.id
            }
        ))
        self.assertContains(
            response, self.IMG_TAG, count=None, status_code=200,
            msg_prefix=f'Тэг "{self.IMG_TAG}" не найден на странице поста',
            html=False
        )

    def test_tag_exist_on_post_list_pages(self):
        """На главной странице, на странице профайла и на странице группы пост
        с картинкой отображается корректно, с тегом <img>."""
        self.create_post_with_temporary_image()
        urls = ['index', 'profile', 'group']
        for url in urls:
            with self.subTest(url=url):
                kwargs = {}
                if url == 'profile':
                    kwargs = {'username': self.auth_user}
                if url == 'group':
                    kwargs = {'slug': self.group.slug}
                response = self.auth_client.get(reverse(url, kwargs=kwargs))
                self.assertContains(
                    response, self.IMG_TAG, count=None, status_code=200,
                    msg_prefix=(
                        f'Тэг "{self.IMG_TAG}" не найден на странице "{url}"'
                    ),
                    html=False
                )

    def test_impossible_load_non_image_file_in_post(self):
        """Проверка, что срабатывает защита от загрузки файлов не-графических
         форматов."""
        file_mock = mock.MagicMock(spec=File, name='test.txt')
        response = self.auth_client.post(
            reverse('new_post'), data={
                'text': self.TEST_TEXT_1,
                'group': self.group.pk,
                'author': self.auth_user,
                'image': file_mock
            }
        )
        self.assertFormError(
            response, 'form', 'image', (
                'Загрузите правильное изображение. Файл, который вы '
                'загрузили, поврежден или не является изображением.'),
            msg_prefix='Удалось загрузить в пост не изображение'
        )


class PostFollowTest(CacheNotRequiredTest):
    def test_auth_user_can_follow_another_users(self):
        """Авторизованный пользователь может подписываться на других
        пользователей."""
        self.auth_client.get(reverse(
            'profile_follow', kwargs={'username': self.no_auth_user.username}
        ))
        following = Follow.objects.all().exists()
        self.assertTrue(following, msg='Не удалось подписаться')

    def test_auth_user_can_unfollow_another_users(self):
        """Авторизованный пользователь может удалять их из подписок других
        пользователей."""
        Follow.objects.create(user=self.auth_user, author=self.no_auth_user)
        self.auth_client.get(reverse(
            'profile_unfollow',
            kwargs={'username': self.no_auth_user.username}
        ))
        following = Follow.objects.all().exists()
        self.assertFalse(following, msg='Не удалось отписаться')

    def test_users_post_available_to_followers(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
        подписан."""
        Follow.objects.create(user=self.auth_user, author=self.no_auth_user)
        self.create_post(self.TEST_TEXT_1, self.group, self.no_auth_user)
        response = self.auth_client.get(reverse('follow_index'))
        self.assertContains(
            response, self.TEST_TEXT_1, status_code=200,
            msg_prefix=f'Пользователь не видит записей по подписке',
            html=False,
        )

    def test_users_post_unavailable_to_not_followers(self):
        """Новая запись пользователя не появляется в ленте тех, кто на него
        не подписан."""
        self.create_post(self.TEST_TEXT_1, self.group, self.no_auth_user)
        response = self.auth_client.get(reverse('follow_index'))
        self.assertNotContains(
            response, self.TEST_TEXT_1, status_code=200,
            msg_prefix=f'Пользователь видит записи не по подписке',
            html=False,
        )


class PostCommentTest(CacheNotRequiredTest):
    def test_auth_user_can_comment_posts(self):
        """Авторизированный пользователь может комментировать посты."""
        self.create_post(self.TEST_TEXT_1, self.group, self.no_auth_user)
        self.auth_client.post(reverse(
            'add_comment', kwargs={
                'username': self.no_auth_user.username,
                'post_id': self.post_id
            }
        ), data={'text': self.TEST_TEXT_2})
        comment_exist = Comment.objects.filter(text=self.TEST_TEXT_2).exists()
        self.assertTrue(
            comment_exist,
            msg='Не удалось оставить комментарий авторизованному пользователю'
        )

    def test_no_auth_user_cant_comment_posts(self):
        """Не авторизированный пользователь не может комментировать посты."""
        self.create_post(self.TEST_TEXT_2, self.group, self.auth_user)
        self.no_auth_client.post(reverse(
            'add_comment', kwargs={
                'username': self.auth_user.username,
                'post_id': self.post_id
            }
        ), data={'text': self.TEST_TEXT_3})
        comment_exist = Comment.objects.filter(text=self.TEST_TEXT_3).exists()
        self.assertFalse(
            comment_exist,
            msg='Удалось оставить комментарий неавторизованному пользователю'
        )


class CacheRequiredPostTest(BaseTest):
    """Предоставляет запуск тестов с кэшированием."""

    def test_verify_cache_index_page(self):
        """Проверка работы кэша главной страницы - запись не должна
        появляться на странице index после кэширования."""
        page = 'index'
        self.create_post(self.TEST_TEXT_1, self.group, self.auth_user)
        self.auth_client.get(reverse(page))
        self.create_post(self.TEST_TEXT_3, self.group, self.auth_user)
        response = self.auth_client.get(reverse(page))
        self.assertNotContains(
            response, self.TEST_TEXT_3, status_code=200,
            msg_prefix=f'Найден текст записи на странице {page}',
            html=False,
        )
