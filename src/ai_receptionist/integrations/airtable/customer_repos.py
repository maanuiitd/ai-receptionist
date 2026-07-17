from dotenv import load_dotenv
import os, requests
from functools import partial
from pyairtable.orm import Model
from pyairtable.orm import fields as F

load_dotenv()

class Customer(Model):
    class Meta:
        api_key =  partial(os.environ.get, 'AIRTABLE_API_KEY')
        base_id = 'appjaiC3Zpaz5UOcl'
        table_name = 'tblymFoaLi7BvkbUb'

    name = F.TextField('Name')
    phone = F.PhoneNumberField('Phone')
    email = F.EmailField('Email')


__all__ = ['Customer', 'CustomerAlreadyExistsError', 'CustomerCreationError']

class CustomerAlreadyExistsError(Exception):
    """
    Email already registered.
    """

class CustomerCreationError(Exception):
    """Record creation failed due to technical reasons (API/network/auth)"""

def is_record_exist(email: str) -> bool:
    formula = Customer.email.eq(email)
    result = Customer.all(formula=formula)
    return False if len(result) == 0 else True

# Object for record creation
def createCustomer(email: str, name: str, phone:int) -> Customer:
    customer=Customer(
        name=name,
        email=email,
        phone=phone,
    )
    if is_record_exist(customer.email):
        raise CustomerAlreadyExistsError(
            f"A customer with email {customer.email} already exists."
        )
    
    try:
        customer.save()
    except requests.exceptions.HTTPError as e:
        raise CustomerCreationError(f"Airtable API error: {e}") from e
    except requests.exceptions.RequestException as e:
        raise CustomerCreationError(f"Network error while saving: {e}") from e
    
    return customer