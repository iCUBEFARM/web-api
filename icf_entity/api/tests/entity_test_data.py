import os
from django.conf import settings

ICF_TYPES = [
    {
        "content_type_model_name": "entity",
        "name": "entity"
    },
    {
        "content_type_model_name": "job",
        "name": "job"
    },

]

CREDIT_ACTIONS = [
    {
        "action": "purchase_credits",
        "action_desc": "purchase_credits",
        "credit_required": 0,
        "interval": 0,
        "type": "entity"
    }
]

CATEGORIES = [
    {
        "name": "Healthcare Industry",
        "description": "Healthcare Industry",
        "type": "entity"
    }
]

INDUSTRIES = [
    {
        "industry": "Biotech",
        "description": "Biotech"
    }
]

SECTORS = [
    {
        "sector": "Healthcare",
        "description": "Healthcare"
    }
]

COMPANY_SIZE = [
    {
        "size": "Small 11 - 100 Employees",
        "description": "Small 11 - 100 Employees"

    }
]

USER_DATA = [
    {
        "mobile": "+919845853541",
        "email": "email@testentity.com",
        "password": "tct@0102",
        "first_name": "TestEntity",
        "last_name": "Admin"
    }
]
#"password": "pbkdf2_sha256$36000$JcJxqzIF4Zgd$H/8bh/AJhADCMjOR90OyMDmZeTQIWsnVu8DVGdlHgfM=",

fields = ["name", "email", "phone", "alternate_phone", "website", "address", "industry",
          "sector", "slug", ]
CREATE_ENTITIES = [
    # Valid
    {
        "name": "Test Entity1",
        "email": "email@testentity1.com",
        "phone": "+912345698765",
        "alternate_phone": "+912345698766",
        "website": "https://www.google.com",
        "industry": "Biotech",
        "sector": "Healthcare",
        "address": {
            "address_1": "1282",
            "address_2": "HSR Layout",
            "city": "Bangalore"
        },
    "description": "Test Entity1 Description"

    },
    # Invalid, without phone
    {
        "name": "Test Entity1",
        "email": "email@testentity1.com",
        "description": "Test Entity1 Description"
    },
]

UPDATE_ENTITIES = [
    {
        "address": {
            "address_1": "1282",
            "address_2": "HSR Layout",
            "city": "Bangalore"
        },
        "name": "Test Entity1",
        "email": "email@testentity1.com",
        "phone": "+912345698765",
        "alternate_phone": "+912345698766",
        "website": "https://www.google.com",
        "industry": "Biotech",
        "sector": "Healthcare",
        "company_size": "Small 11 - 100 Employees",
        "description": "Test Entity1 Description",
        "category": "Healthcare Industry",
        "linked_in": "",
        "twitter": "",
        "schedule_appointment": "https://www.calendly.com"
    }
]

LOCATION = {
    "country": "India",
    "state": "Karnataka",
    "city": "Bangalore"
}
TEST_FILES_PATH = os.path.join(settings.BASE_DIR, 'icf_entity', 'api', 'tests', 'files')

ENTITY_BROCHURES = [
    {
        "brochure_name": "Word Document",
        "entity": "",
        "brochure": "test-word-doc.docx"
    },
    {
        "brochure_name": "Pdf Document",
        "entity": "",
        "brochure": "test-pdf-doc.pdf"
    }
]

ENTITY_PROMOTIONAL_VIDEOS = [
    {
        "promotional_video_name": "Test Promotional Video1",
        "entity": "",
        "promotional_video_url": "https://test.promotionalvideourl1.com"
    },
    {
        "promotional_video_name": "Test Promotional Video2",
        "entity": "",
        "promotional_video_url": "https://test.promotionalvideourl2.com"
    },
]


