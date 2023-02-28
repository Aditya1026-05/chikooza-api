from rest_framework.exceptions import ValidationError

from common.constant import (
    ERROR,
    MESSAGE,
    PUBLIC_ID_LENGTH_VALIDATION,
    RECORD_NOT_FOUND,
)
from common.utils import validation_return_response


def id_validation_check(object_id, id_error_type):
    """
    This function is created to validate ids.
    :param object_id:
    :param id_error_type:
    :raise ValidationError
    """
    try:

        if object_id is not None:
            int(object_id)
    except ValueError:
        raise ValidationError({ERROR: id_error_type.format(object_id)})


def validate_url_value(public_id, key_name):
    """
    This function is created to validate ids.
    :param public_id:
    :param key_name:
    :raise ValidationError
    """
    try:
        if public_id is not None:
            int(public_id)
            if public_id == "0" or public_id == 0:
                raise validation_return_response(
                    field=MESSAGE, message=RECORD_NOT_FOUND
                )
            elif len(str(public_id)) > PUBLIC_ID_LENGTH_VALIDATION:
                raise validation_return_response(
                    field=MESSAGE, message=RECORD_NOT_FOUND
                )
    except ValueError:
        raise validation_return_response(field=MESSAGE, message=RECORD_NOT_FOUND)


def validate_url_value_for_string(type_of_content, key_name):
    """
    This function is created to validate ids.
    :param type_of_content:
    :param key_name:
    :raise ValidationError
    """
    if type_of_content is not None:
        if type_of_content not in [
            "terms-and-conditions",
            "privacy-policy",
            "about",
            "subscription",
            "covid19",
            "pricing",
        ]:
            raise validation_return_response(field=MESSAGE, message=RECORD_NOT_FOUND)
