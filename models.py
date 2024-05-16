from typing import Union


from pydantic import BaseModel


class User(BaseModel):
    name: str
    description: Union[str, None] = None
    price: float
    tax: Union[float, None] = None