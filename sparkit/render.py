from dataclasses import dataclass
from typing import List, Dict

# This module takes care of rendering SQL
# users can implement other RenderingContextConfig then the ones provided here

@dataclass
class RenderingContextConfig:
    """
    Config to handle sql rendering under specific contexts.
    Contexts are leading keywords i.e. SELECT, FROM, WHERE, CASE ...

    Arguments:
        indent_str: str - the symbol to be used for indentation, default = ''
        comma_line_break: bool - should insert a line break when encountering a comma?, default = False
        break_line: Tuple[str,...] - tuple of context symbols to break line when met
        spacing: str - the str to use to space between tokens
    """
    break_on_change_context: bool=False
    increase_indent_in_context_change: bool=False
    indent_str: str=''
    comma_line_break: bool=False
    left_parenthesis_break: bool=False
    right_parenthesis_break: bool=False
    spacing: str = ' '

    def indent(self, indent_depth: int) -> str:
        return self.indent_str*indent_depth
    
    def handle_token(self, token: str, indent_depth: int) -> str:
        """the behavior of this function is such that it always returns the str 
        in the indent ready for the next token"""
        match token:
            case ',' if self.comma_line_break:
                return token + '\n' + self.indent(indent_depth)
            case '(' if self.left_parenthesis_break:
                return token + '\n' + self.indent(indent_depth)
            case ')' if self.right_parenthesis_break:
                return token + '\n' + self.indent(indent_depth)
            case token:
                return token + self.spacing


class SqlRenderer:

    @staticmethod
    def render(tokens: List[str], 
               context2config: Dict[str, RenderingContextConfig]={},
               ) -> str:
        indent_depth = 0
        indent_dict = {}
        current_config = None
        flat_config = RenderingContextConfig()
        result = ''
        for token in tokens:
            # context changes are handled here
            # the context changing symbol is not added by the config
            if token in context2config.keys(): # when context is changed
                if current_config is not None:
                # if the indent was increased for the current config
                # reduce it by 1 
                    if current_config.increase_indent_in_context_change:
                        indent_depth = max(0, indent_depth-1)
 
                
                # replace config
                current_config = context2config[token] 
                if current_config.break_on_change_context:
                    result += '\n' + current_config.indent(indent_depth) + token
                if current_config.increase_indent_in_context_change:
                    indent_depth += 1
                    result += '\n' + current_config.indent(indent_depth)
            else:
                if current_config is None:
                    result += flat_config.handle_token(token=token, indent_depth=indent_depth)
                else:
                    result += current_config.handle_token(token=token, indent_depth=indent_depth)
        return result.strip()


