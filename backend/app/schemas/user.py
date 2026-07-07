from pydantic import BaseModel


class PresetSourceOut(BaseModel):
    key: str
    name: str
    url: str
    type: str
    description: str
    category: str


class UserSourcesIn(BaseModel):
    enabled_keys: list[str]


class UserInterestsIn(BaseModel):
    interests: list[str]
