from django import forms

from .models import Post, Topic, Board
from django.contrib.auth.models import User

class NewBoardForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={'rows': 5, 'placeholder': 'What is this about?'}
        ),
        max_length=4000,
        help_text='The max length of the text is 4000.'
    )
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, 
        queryset=User.objects.all(), 
        required=False
    )

    class Meta:
        model = Board
        fields = ['name', 'description', 'private', 'members']


class NewTopicForm(forms.ModelForm):
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={'rows': 5, 'placeholder': 'What is in your mind?'}
        ),
        max_length=4000,
        help_text='The max length of the text is 4000.'
    )

    class Meta:
        model = Topic
        fields = ['subject', 'message']


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['message', ]
