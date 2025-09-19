# pip install langgraph langchain langchain-openai pydantic pandas
from typing import Optional, Literal
import pandas as pd
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import MessagesState

# ----- ваши данные/хелперы -----
country_map = {
    "IT": "Италия", "FR": "Франция", "ES": "Испания", "RU": "Россия",
    "PT": "Португалия", "AR": "Армения", "CL": "Чили", "AU": "Австралия",
    "GE": "Грузия", "ZA": "ЮАР", "US": "США", "NZ": "Новая Зеландия",
    "DE": "Германия", "AT": "Австрия", "IL": "Израиль", "BG": "Болгария",
    "GR": "Греция",
}
revmap = {v.lower(): k for k, v in country_map.items()}

# Пример таблицы (замените на свою pl/df)
pl = pd.DataFrame([
    {"Name": "Shiraz Alpha", "Country": "AU",
        "Color": "Красное", "Acidity": "Сухое", "Price": 12.5},
    {"Name": "Chardonnay Gold", "Country": "AU",
        "Color": "Белое", "Acidity": "Сухое", "Price": 9.9},
    {"Name": "Merlot Breeze", "Country": "AU",
        "Color": "Красное", "Acidity": "Сухое", "Price": 8.7},
])

# ----- Pydantic-схема входа -----


class SearchWinePriceList(BaseModel):
    """Эта функция позволяет искать вина в прайс-листе по одному или нескольким параметрам."""
    name: Optional[str] = Field(default=None, description="Название вина")
    country: Optional[str] = Field(
        default=None, description="Страна на русском языке")
    acidity: Optional[Literal["сухое", "полусухое", "сладкое", "полусладкое"]] = Field(
        default=None, description="Кислотность")
    color: Optional[Literal["красное", "белое", "розовое"]
                    ] = Field(default=None, description="Цвет вина")
    sort_order: Optional[Literal["most expensive", "cheapest", "random", "average"]] = Field(
        default=None, description="Порядок выдачи")
    what_to_return: Optional[Literal["wine info", "price"]] = Field(
        default=None, description="Что вернуть")

# ----- тулза (функция), аннотированная для LLM -----


@tool("search_wine_price_list", args_schema=SearchWinePriceList)
def find_wines_tool(
    name: Optional[str] = None,
    country: Optional[str] = None,
    acidity: Optional[str] = None,
    color: Optional[str] = None,
    sort_order: Optional[str] = None,
    what_to_return: Optional[str] = None,
) -> str:
    """Ищет вина в прайс-листе по фильтрам и возвращает человеко-читаемый список."""
    x = pl.copy()
    if country and country.lower() in revmap:
        x = x[x["Country"] == revmap[country.lower()]]
    if acidity:
        x = x[x["Acidity"].str.lower() == acidity.lower()]
    if color:
        x = x[x["Color"].str.lower() == color.lower()]
    if name:
        x = x[x["Name"].str.lower().str.contains(name.lower())]

    if sort_order and len(x) > 0:
        if sort_order == "cheapest":
            x = x.sort_values(by="Price", ascending=True)
        elif sort_order == "most expensive":
            x = x.sort_values(by="Price", ascending=False)

    if x is None or len(x) == 0:
        return "Подходящих вин не найдено."

    lines = [
        f"{row['Name']} ({country_map.get(row['Country'],'Неизвестно')}) — {row['Price']}"
        for _, row in x.head(10).iterrows()
    ]
    return "Вот какие вина были найдены:\n" + "\n".join(lines)
