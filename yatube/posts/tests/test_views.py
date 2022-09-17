from http import HTTPStatus

import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django import forms

from ..models import Group, Post, User, Follow
from ..constants import POSTS_PAGE


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.auth_user = User.objects.create_user(username='TestAuthUser')
        cls.new_user = User.objects.create_user(username='NewUser')
        cls.small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostTests.auth_user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostTests.author)
        self.authorized_client_user = Client()
        self.authorized_client_user.force_login(PostTests.new_user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        page_names_templates = {
            reverse(
                'posts:index'
            ): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.pk}
            ): 'posts/create_post.html',
            reverse(
                'posts:post_create'
            ): 'posts/create_post.html',
        }
        for reverse_name, template in page_names_templates.items():
            with self.subTest(template=template):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон главной страницы сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post_id = response.context.get('page_obj')[0].id
        post_text = response.context.get('page_obj')[0].text
        post_author = response.context.get('page_obj')[0].author.username
        group_post = response.context.get('page_obj')[0].group.title
        post_image = response.context.get('page_obj')[0].image
        self.assertEqual(post_id, self.post.id)
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_author, self.post.author.username)
        self.assertEqual(group_post, self.post.group.title)
        self.assertEqual(post_image, self.post.image)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        url = reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}
        )
        response = self.authorized_client.get(url)
        group_title = response.context.get('group').title
        group_description = response.context.get('group').description
        group_slug = response.context.get('group').slug
        self.assertEqual(group_title, self.group.title)
        self.assertEqual(group_description, self.group.description)
        self.assertEqual(group_slug, self.group.slug)
        post_id = response.context.get('page_obj')[0].id
        post_text = response.context.get('page_obj')[0].text
        post_author = response.context.get('page_obj')[0].author.username
        group_post = response.context.get('page_obj')[0].group.title
        post_image = response.context.get('page_obj')[0].image
        self.assertEqual(post_id, self.post.id)
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_author, self.post.author.username)
        self.assertEqual(group_post, self.group.title)
        self.assertEqual(post_image, self.post.image)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        url = reverse('posts:profile', kwargs={'username': PostTests.author})
        response = self.authorized_client_author.get(url)
        post_text = response.context.get('page_obj')[0].text
        post_author = response.context.get('page_obj')[0].author.username
        group_post = response.context.get('page_obj')[0].group.title
        post_image = response.context.get('page_obj')[0].image
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_author, self.post.author.username)
        self.assertEqual(group_post, self.post.group.title)
        self.assertEqual(post_image, self.post.image)
        author_username = response.context.get('author').username
        self.assertEqual(author_username, self.author.username)
        following = response.context.get('following')
        self.assertFalse(following)
        self.assertIsInstance(following, bool)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        url = reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        response = self.authorized_client_author.get(url)
        post_text = response.context.get('post').text
        post_id = response.context.get('post').id
        post_author = response.context.get('post').author
        group_post = response.context.get('post').group
        post_image = response.context.get('post').image
        self.assertEqual(post_id, self.post.id)
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_author, self.author)
        self.assertEqual(group_post, self.group)
        self.assertEqual(post_image, self.post.image)

    def test_create_post_edit_show_correct_context(self):
        """Шаблон редактирования поста create_post сформирован
        с правильным контекстом.
        """
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        response = self.authorized_client_author.get(url)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for field, expected in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected)
        post_id_context = response.context.get('post_id')
        self.assertEqual(post_id_context, self.post.pk)
        is_edit_context = response.context.get('is_edit')
        self.assertTrue(is_edit_context)
        self.assertIsInstance(is_edit_context, bool)

    def test_create_post_show_correct_context(self):
        """Шаблон создания поста create_post сформирован
        с правильным контекстом.
        """
        url = reverse('posts:post_create')
        response = self.authorized_client.get(url)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for field, expected in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_home(self):
        """Созданный пост отобразился на главной странице."""
        new_group = Group.objects.create(
            title='Новая группа',
            slug='new-group',
            description='Описание новой группы'
        )
        test_post = Post.objects.create(
            author=self.author,
            group=new_group,
            text='Пост для проверки расположения',
            image=self.uploaded,
        )
        response = self.client.get(reverse('posts:index'))
        page_obj_context_1 = response.context['page_obj'].object_list[:1]
        self.assertIn(test_post, page_obj_context_1)

    def test_create_post_show_group_list(self):
        """Созданный пост отобразился на странице группы."""
        new_group = Group.objects.create(
            title='Новая группа',
            slug='new-group',
            description='Описание новой группы'
        )
        test_post = Post.objects.create(
            author=self.author,
            group=new_group,
            text='Пост для проверки расположения',
            image=self.uploaded,
        )
        response = self.client.get(reverse(
            'posts:profile',
            kwargs={
                'username': test_post.author.username
            }
        ))
        page_obj_context_2 = response.context['page_obj'].object_list[:1]
        self.assertIn(test_post, page_obj_context_2)

    def test_create_post_show_profile(self):
        """Созданный пост отобразился в профиле пользователя."""
        new_group = Group.objects.create(
            title='Новая группа',
            slug='new-group',
            description='Описание новой группы'
        )
        test_post = Post.objects.create(
            author=self.author,
            group=new_group,
            text='Пост для проверки расположения',
            image=self.uploaded,
        )
        response = self.client.get(reverse(
            'posts:group_list',
            kwargs={
                'slug': test_post.group.slug
            }
        ))
        page_obj_context_3 = response.context['page_obj'].object_list[:1]
        self.assertIn(test_post, page_obj_context_3)

    def test_post_not_another_group(self):
        """Созданный пост не попал в группу, для которой не предназначен"""
        another_group = Group.objects.create(
            title='Дополнительная тестовая группа',
            slug='test-another-slug',
            description='Тестовое описание дополнительной группы',
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': another_group.slug})
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_commenting_is_available_only_authorized_user(self):
        """Комментирование доступно только авторизованному пользователю."""
        form_data = {
            'text': 'Комментарий',
        }
        response_authorized = self.authorized_client.get(
            reverse('posts:add_comment', kwargs={
                'post_id': self.post.pk}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(response_authorized.status_code, HTTPStatus.OK)
        response_not_authorized = self.client.get(
            reverse('posts:add_comment', kwargs={
                'post_id': self.post.pk}
            ),
            data=form_data
        )
        self.assertEqual(
            response_not_authorized.status_code,
            HTTPStatus.FOUND
        )

    def test_cache_index(self):
        """Проверка кэша на главной странице."""
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        response_1 = response.content
        post_deleted = Post.objects.get(id=self.post.pk)
        post_deleted.delete()
        response_again = self.authorized_client.get(
            reverse('posts:index')
        )
        response_2 = response_again.content
        self.assertTrue(response_1 == response_2)
        cache.clear()
        response_again_2 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_3 = response_again_2.content
        self.assertFalse(response_1 == response_3)

    def test_follow_user(self):
        """Тест подписки на другого пользователя."""
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.author.username})
        )
        follow_exist = Follow.objects.filter(
            user=self.auth_user,
            author=self.author,
        ).exists()
        self.assertTrue(follow_exist)

    def test_unfollow_user(self):
        """Тест отписки от другого пользователя."""
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.author.username}))
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author.username}))
        follow_exist = Follow.objects.filter(
            user=self.auth_user,
            author=self.author,
        ).exists()
        self.assertFalse(follow_exist)

    def test_followers_see_followed_author_post(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
        подписан."""
        Follow.objects.create(
            user=self.auth_user,
            author=self.author,
        )
        response_subscribed = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        page_object = response_subscribed.context['page_obj'][0]
        self.assertEqual(page_object.text, self.post.text)

    def test_unfollowers_dont_see_author_posts(self):
        """Новая запись пользователя не появляется в ленте тех, кто на него
        не подписан."""
        Follow.objects.create(
            user=self.auth_user,
            author=self.author,
        )
        Post.objects.create(
            text='Пост от третьего юзера',
            author=self.new_user,
        )
        response_unsubscribed = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        page_object_unsub = response_unsubscribed.context['page_obj'][0]
        self.assertEqual(page_object_unsub, self.post)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.auth_user = User.objects.create_user(username='TestAuthUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.posts = [
            Post(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group,
            )
            for i in range(13)
        ]
        Post.objects.bulk_create(cls.posts)

    def test_first_page_contains_ten_records(self):
        """Количество постов на страницах index, group_list, profile
        равно 10.
        """
        urls = (
            reverse(
                'posts:index'
            ),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ),
        )
        for url in urls:
            response = self.client.get(url)
            amount_posts = len(response.context.get('page_obj').object_list)
            self.assertEqual(amount_posts, POSTS_PAGE)

    def test_second_page_contains_three_records(self):
        """Количество постов на страницах index, group_list, profile
        равно 3.
        """
        urls = (
            reverse(
                'posts:index'
            ) + '?page=2',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ) + '?page=2',
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ) + '?page=2',
        )
        for url in urls:
            response = self.client.get(url)
            amount_posts = len(response.context.get('page_obj').object_list)
            self.assertEqual(amount_posts, 3)