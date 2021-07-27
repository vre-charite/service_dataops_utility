import re
from models.base_models import EAPIResponseCode


def validate_taglist(taglist, internal=False):
    tag_requirement = re.compile("^[a-z0-9-]{1,32}$")
    for tag in taglist:
        if tag == "copied-to-core" and not internal:
            return False, {
                "error": 'invalid tag, tag is reserved',
                "code": EAPIResponseCode.forbidden
            }
        if not re.search(tag_requirement, tag):
            return False, {
                "error": 'invalid tag, must be 1-32 characters lower case, number or hyphen',
                "code": EAPIResponseCode.forbidden
            }

    # duplicate check
    if len(taglist) != len(set(taglist)):
        return False, {
            "error": 'duplicate tags not allowed',
            "code": EAPIResponseCode.bad_request
        }

    if len(taglist) > 10:
        return False, {
            "error": 'limit of 10 tags',
            "code": EAPIResponseCode.bad_request
        }
    return True, {}

