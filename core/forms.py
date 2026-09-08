from django import forms
from .models import SchoolSettings, School

class SchoolSettingsForm(forms.ModelForm):
    class Meta:
        model = SchoolSettings
        exclude = ['school', 'created_at', 'updated_at']
        widgets = {
            'school_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'school_address': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg', 'rows': 3}),
            'school_phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'school_email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'school_website': forms.URLInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'school_motto': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'report_card_title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'header_text': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg', 'rows': 3}),
            'footer_text': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg', 'rows': 3}),
            'show_grade_scale': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'show_teacher_signature': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'show_head_teacher_signature': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'grade_a_min': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_b_min': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_c_min': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_d_min': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_e_min': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_a_label': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_b_label': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_c_label': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_d_label': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'grade_e_label': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'}),
            'primary_color': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg', 'type': 'color'}),
        }