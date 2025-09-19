from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

from ..tools.wine_tool import find_wines_tool


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


class Agent:
    def __init__(self):
        self.memory = InMemorySaver()
        self.config = {"configurable": {"thread_id": "1"}}
        self.tool_node = ToolNode([find_wines_tool])
        self.llm = init_chat_model("openai:gpt-4.1")
        self.llm_with_tools = self.llm.bind_tools([find_wines_tool])
        self.graph = self._create_graph()

    def _create_graph(self):
        graph_builder = StateGraph(State)

        # The first argument is the unique node name
        # The second argument is the function or object that will be called whenever
        # the node is used.
        graph_builder.add_node("chatbot", self.chatbot)
        graph_builder.add_node("tools", self.tool_node)

        graph_builder.add_edge(START, "chatbot")

        graph_builder.add_conditional_edges("chatbot", tools_condition)

        graph_builder.add_edge("tools", "chatbot")

        graph_builder.add_edge("chatbot", END)

        return graph_builder.compile(checkpointer=self.memory)

    def _create_config(self, thread_id: str):
        return {"configurable": {"thread_id": thread_id}}

    def chatbot(self, state: State):
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def stream_graph_updates(self, user_input: str):
        events = self.graph.stream(
            {"messages": [{"role": "user", "content": user_input}]}, self._create_config('default'), stream_mode='values')

        for event in events:
            event["messages"][-1].pretty_print()


if __name__ == "__main__":
    load_dotenv()

    agent = Agent()

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            agent.stream_graph_updates(user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            agent.stream_graph_updates(user_input)
            break
