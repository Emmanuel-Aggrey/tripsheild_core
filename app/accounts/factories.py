import factory
from app.test.base import BaseTest

from .models import User


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = BaseTest.get_db()
        sqlalchemy_session_persistence = "commit"

    is_active = True
    email = factory.Faker("email")
    hashed_password = factory.Faker("password")
    first_name = factory.Faker("name")
    last_name = factory.Faker("name")
    phone_number = factory.Faker("phone_number")
    profile_picture = factory.Faker("image_url")
    address = factory.Faker("address")
    date_of_birth = factory.Faker("date_of_birth")
    gender = factory.Faker("random_element", elements=["male", "female"])
    occupation = factory.Faker("job")
    ghana_card_number = factory.Faker("numerify", text="GHA-#########-#")
