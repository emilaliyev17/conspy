"""Forms for the core application."""

from django import forms

from .models import ActiveState


class ActiveStateForm(forms.ModelForm):
    """Form for creating and updating ActiveState records."""

    class Meta:
        model = ActiveState
        fields = ['state_code', 'state_name', 'deal_count', 'deal_volume', 'is_active']

    def clean_state_code(self):
        code = (self.cleaned_data.get('state_code') or '').strip().upper()
        if len(code) != 2:
            raise forms.ValidationError('Use the 2-letter state abbreviation (e.g. TX, CA).')
        return code

