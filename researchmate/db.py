import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS papers (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, authors TEXT DEFAULT '', abstract TEXT DEFAULT '',
          year INTEGER, doi TEXT DEFAULT '', url TEXT DEFAULT '', source TEXT DEFAULT '',
          saved_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, paper_id TEXT,
          text TEXT NOT NULL, summary TEXT DEFAULT '', added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chunks (
          id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER NOT NULL, page INTEGER,
          section TEXT DEFAULT '', text TEXT NOT NULL,
          FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        columns={row['name'] for row in c.execute('PRAGMA table_info(documents)')}
        if 'summary' not in columns:
            c.execute("ALTER TABLE documents ADD COLUMN summary TEXT DEFAULT ''")

def list_papers():
    with connect() as c: return [dict(r) for r in c.execute('SELECT * FROM papers ORDER BY saved_at DESC')]

def save_paper(p):
    with connect() as c:
        c.execute('INSERT OR REPLACE INTO papers(id,title,authors,abstract,year,doi,url,source) VALUES(?,?,?,?,?,?,?,?)',
                  (p['id'],p['title'],p.get('authors',''),p.get('abstract',''),p.get('year'),p.get('doi',''),p.get('url',''),p.get('source','')))

def delete_paper(pid):
    with connect() as c: c.execute('DELETE FROM papers WHERE id=?',(pid,))

def add_document(name, text, paper_id=None):
    with connect() as c:
        cur=c.execute('INSERT INTO documents(name,paper_id,text) VALUES(?,?,?)',(name,paper_id,text))
        return cur.lastrowid

def add_chunks(document_id, chunks):
    with connect() as c:
        c.executemany('INSERT INTO chunks(document_id,page,section,text) VALUES(?,?,?,?)',
                      [(document_id,x.get('page'),x.get('section',''),x['text']) for x in chunks])

def save_document_summary(document_id, summary):
    with connect() as c:
        c.execute('UPDATE documents SET summary=? WHERE id=?',(summary,document_id))

def list_documents():
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT d.*, p.title AS paper_title FROM documents d LEFT JOIN papers p ON p.id=d.paper_id ORDER BY d.added_at DESC')]

def delete_document(doc_id):
    with connect() as c:
        c.execute('DELETE FROM chunks WHERE document_id=?',(doc_id,)); c.execute('DELETE FROM documents WHERE id=?',(doc_id,))

def all_chunks(document_ids=None):
    with connect() as c:
        sql='SELECT c.*, d.name FROM chunks c JOIN documents d ON d.id=c.document_id'
        args=[]
        if document_ids:
            sql += ' WHERE c.document_id IN ('+','.join('?' for _ in document_ids)+')'; args=list(document_ids)
        return [dict(r) for r in c.execute(sql,args)]

def save_report(title, body):
    with connect() as c: c.execute('INSERT INTO reports(title,body) VALUES(?,?)',(title,body))
