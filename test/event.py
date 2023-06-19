from sqlalchemy import create_engine, Column, Integer, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///example.db')
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Example(Base):
    __tablename__ = 'example'
    id = Column(Integer, primary_key=True)
    value = Column(Integer)


@event.listens_for(Example.value, 'set')
def value_set(target, value, oldvalue, initiator):
    if oldvalue == 0 and value == 1:
        print("Value changed from 0 to 1 in Example table")


Base.metadata.create_all(engine)

session = Session()
example = Example(value=0)
session.add(example)
session.commit()

example.value = 1
session.commit()
