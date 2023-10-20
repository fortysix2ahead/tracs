from typing import List

def style( *items: str, style: str ) -> List[str]:
	return [f'[{style}]{i}[/{style}]' for i in items]
