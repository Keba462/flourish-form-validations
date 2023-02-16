from django.apps import apps as django_apps
from django.forms import ValidationError
from django.conf import settings
from edc_constants.constants import YES, POS, NEG, NO, NOT_APPLICABLE
from edc_form_validators import FormValidator
from flourish_caregiver.helper_classes import MaternalStatusHelper
from flourish_caregiver.constants import PNTA
from .crf_form_validator import FormValidatorMixin


class RelationshipFatherInvolvementFormValidator(FormValidatorMixin, FormValidator):

    anc_onschedule_model = 'flourish_caregiver.onschedulecohortaantenatal'
    maternal_delivery_model = 'flourish_caregiver.maternaldelivery'

    @property
    def anc_onschedule_model_cls(self):
        return django_apps.get_model(self.anc_onschedule_model)

    @property
    def maternal_delivery_model_cls(self):
        return django_apps.get_model(self.maternal_delivery_model)

    def clean(self):

        self.validate_required_fields()

        self.required_if(NO,
                         field='partner_present',
                         field_required='why_partner_absent')
        self.validate_against_hiv_status(cleaned_data=self.cleaned_data)
        self.required_if(NO,
                         field='living_with_partner',
                         field_required='why_not_living_with_partner')

        self.required_if(YES,
                         field='partner_present',
                         field_required='is_partner_the_father')

        self.required_if(YES,
                         field='ever_separated',
                         field_required='times_separated')

        self.required_if(YES,
                         field='contact_info',
                         field_required='partner_cell')
        is_partner_the_father = self.cleaned_data.get('is_partner_the_father', None)
        biological_father_alive = self.cleaned_data.get('biological_father_alive', None)

        if is_partner_the_father and biological_father_alive:
            if is_partner_the_father == YES and biological_father_alive != YES:
                raise ValidationError({
                    'biological_father_alive':
                    'Currently living with the father, check question 5 '
                })

        self.validate_father_involvement()

        super().clean()

    def validate_required_fields(self):
        required_fields = [
            'is_partner_the_father',
            'duration_with_partner',
            'partner_age_in_years',
            'living_with_partner',
            'partners_support',
            'ever_separated',
            'separation_consideration',
            'leave_after_fight',
            'relationship_progression',
            'confide_in_partner',
            'relationship_regret',
            'quarrel_frequency',
            'bothering_partner',
            'kissing_partner',
            'engage_in_interests',
            'happiness_in_relationship',
            'future_relationship',
        ]

        for field in required_fields:
            self.required_if(YES, field='partner_present',
                             field_required=field)

    def validate_father_involvement(self):

        required_fields = [
            'father_child_contact',
            'fathers_financial_support',
        ]

        condition = self.has_delivered
        father_alive = self.cleaned_data.get('biological_father_alive', None)

        for field in required_fields:
            self.required_if_true(
                condition and father_alive == YES,
                field_required=field)

    def validate_against_hiv_status(self, cleaned_data):
        helper = self.maternal_status_helper
        fields = ['disclosure_to_partner',
                  'discussion_with_partner', 'disclose_status']
        if helper.hiv_status == NEG:
            for field in fields:
                if cleaned_data.get(field) and cleaned_data.get(field) != NOT_APPLICABLE:
                    raise ValidationError({
                        field: 'This field is not applicable'
                    })
        else:
            self.not_applicable_if(NO,
                                   field='partner_present',
                                   field_applicable='disclosure_to_partner')

            self.applicable_if(YES, field='disclosure_to_partner',
                               field_applicable='discussion_with_partner'
                               )

            self.applicable_if(NO, field='disclosure_to_partner',
                               field_applicable='disclose_status',
                               )

    def validate_positive_mother(self):
        # Checker when running tests so it does require addition modules
        if settings.APP_NAME != 'flourish_form_validations':
            maternal_visit = self.cleaned_data.get('maternal_visit')
            helper = MaternalStatusHelper(
                maternal_visit, maternal_visit.subject_identifier)

            self.required_if_true(helper.hiv_status == POS,
                                  field_required='disclosure_to_partner')

            self.required_if(YES, field='disclosure_to_partner',
                             field_required='discussion_with_partner')
            self.required_if(NO, field='disclosure_to_partner',
                             field_required='disclose_status')

    @property
    def maternal_status_helper(self):
        cleaned_data = self.cleaned_data
        visit_obj = cleaned_data.get('maternal_visit')
        if visit_obj:
            return MaternalStatusHelper(visit_obj)

    @property
    def has_delivered(self):
        subject_identifier = self.cleaned_data.get('maternal_visit').subject_identifier
        try:
            self.anc_onschedule_model_cls.objects.get(
                subject_identifier=subject_identifier)
        except self.anc_onschedule_model_cls.DoesNotExist:
            return True
        else:
            return self.maternal_delivery_model_cls.objects.filter(
                subject_identifier=subject_identifier).exists()
