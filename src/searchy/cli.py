from re import I
from readline import read_init_file
import typer
from typing import List, Optional

import os
from pathlib import Path
from whoosh.fields import Schema, TEXT, ID
from whoosh import index
from whoosh.index import create_in
from whoosh.qparser import QueryParser

from simple_term_menu import TerminalMenu
from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer

from pygments.lexer import RegexLexer
from pygments.token import *
from prompt_toolkit.styles import Style
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.completion import WordCompleter

style = Style.from_dict({
    # User input (default text).
    '':          '#ff0066',

    # Prompt.
    'pound':    '#00aa00',
})

message = [
    ('class:pound',    '> '),
]


query_completer = WordCompleter(['AND', 'OR', 'NOT'])


class QueryLexer(RegexLexer):
    name = 'Query'
    aliases = ['query']
    filenames = ['*.query']

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'AND', Keyword),
            (r'OR', Keyword),
            (r'NOT', Keyword),
        ]
    }

class MarkdownNote():

    def __init__(self, path):
        self.full_path = os.path.abspath(path)
        self.path = Path(self.full_path)
        self.name = self.path.stem

    def add_to_writer(self, writer):
        with open(self.full_path, encoding='utf-8') as _file:
            writer.add_document(title=self.name, 
                                path=self.full_path, 
                                content=_file.read())

    @classmethod
    def load(cls, path):
        if path.endswith(".md"):
            return cls(path)

def db_index_create(dirpath):
    schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT)
    idx = create_in("indexdir", schema)
    with idx.writer() as writer:
        for _, _, fnames in os.walk(dirpath):
            for f in fnames:
                note = MarkdownNote.load(os.path.join(dirpath, f))
                note.add_to_writer(writer)
    return idx

def db_index(dirpath, reindex=False):
    if reindex:
        return db_index_create(dirpath)
    else:
        return index.open_dir(dirpath)

def db_search(idx, query_string):
    with idx.searcher() as searcher:
        query = QueryParser("content", idx.schema).parse(query_string)
        results = searcher.search(query)
        for result in results:
            yield result

def search(idx, query):
    results = [i['path'] for i in db_search(idx, query)]
    if results:
        terminal_menu = TerminalMenu(results, preview_command="glow {}", preview_size=0.75)
        menu_entry_index = terminal_menu.show()
        if menu_entry_index is not None:
            print(menu_entry_index, results[menu_entry_index])
    else:
        print("No results!")


def main(data: Path = typer.Option(None,
                                   help="Path to dir to be indexed",
                                   exists=True,
                                   file_okay=False,
                                   dir_okay=True,
                                   writable=True,
                                   readable=True,
                                   resolve_path=False,
                                   ),
         query: str = typer.Option(None,
                                   help="Query"),
         reindex: Optional[bool] = typer.Option(True, 
                                                help="Force reindex"),
         ):
    
    idx = db_index(data, reindex)
    
    if query:
        search(idx, query)
    else:
        session = PromptSession(lexer=PygmentsLexer(QueryLexer))

        while True:
            try:
                query = session.prompt(message, 
                                       style=style, 
                                       cursor=CursorShape.BLINKING_UNDERLINE, 
                                       complete_while_typing=False,
                                       completer=query_completer)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            else:
                if query:
                    print(f'Searching: {query}')
                    search(idx, query)
        print('GoodBye!')

app = typer.run(main)