from django import forms
from posts.models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['group', 'text', 'image']
        help_texts = {
            'group': 'Выберите группу, к которой относится запись.',
            'text': 'Введите текст вашей записи в форму.',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        help_texts = {
            'text': 'Введите текст вашей записи в форму.',
        }
