import asyncio
from agentcore.src.orchestrator.graph import compiled_graph

async def main():
    result = await compiled_graph.ainvoke({'run_id':'inspect','company':'Contoso','country':'US','tier':'Standard'})
    print(type(result))
    print(result.keys())
    for key, value in result.items():
        if isinstance(value, dict):
            print('---', key, '---')
            print(list(value.keys())[:50])
        else:
            print('---', key, type(value).__name__, '---')
            print(value)

asyncio.run(main())
