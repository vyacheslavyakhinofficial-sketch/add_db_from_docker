import uvicorn
from fastapi import FastAPI, status, HTTPException, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4

from contextlib import asynccontextmanager
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column
# для подключения к БД и таблицу Task


DATABASE_URL = "postgresql+psycopg://postgres:admin@127.0.0.1:5432/postgres"
# Адрес БД для подключения
engine = create_engine(DATABASE_URL)
# главный объект SQLAlchemy для связи с БД. Через него она открывает подключения и отправляет SQL
SessionLocal = sessionmaker(bind=engine)
# “станок”, который умеет штамповать новые сессии с БД


class Base(DeclarativeBase):
    """Базовый класс для всех моделей таблиц БД"""
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
# базовый класс всех моделей. Наследуется от него = таблица в БД.
# В данном случае у всех дочерних таблиц будет поле id (первичный ключ)


class TaskORM(Base):
    """Модель для таблицы задачи в Базе Данных"""
    __tablename__ = "tasks"
# прописываем схему в БД для задачи через атрибуты класса.
    title: Mapped[str]
    completed: Mapped[bool] = mapped_column(default=False)
# mapped_column и Mapped задают структуру БД для каждого поля: Строковый title и булевый completed


class CategoriesORM(Base):
    __tablename__ = "categories"

    name: Mapped[str]
    completed: Mapped[bool] = mapped_column(default=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield
# Lifespan — возможность выполнять код до и после запуска FastAPI приложения.
# В данном случае создать нужные таблицы, если их ещё нет


app = FastAPI(lifespan=lifespan)

def get_db():
    """Функция для создания сессий с БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# yield в get_db используется, чтобы не просто вернуть сессию, а закрыть её после работы.
# Если не закрыть – в какой-то момент лимит подключений закончится


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
)
# совместное использование ресурсов между frontend и backend




tasks: list[Tasks] = []


class Tasks(BaseModel):
    id: str
    title: str
    completed: bool

class TasksCreate(BaseModel):
    title: str

class TasksUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None


def task_to_model(task: TaskORM) -> Tasks:
    """Конвертация объекта ORM в Pydantic"""
    return Tasks(id=task.id, title=task.title, completed=task.completed)




@app.get("/tasks", response_model=list[Tasks], status_code=status.HTTP_200_OK)
def get_tasks(db: Tasks = Depends(get_db)) -> list[Tasks]:
    """Получить список задач"""
    tasks = db.scalars(select(TaskORM)).all()
    return [task_to_model(task) for task in tasks]


@app.post("/tasks", response_model=Tasks, status_code=status.HTTP_201_CREATED)
def create_tasks(payload: TasksCreate, db: Session = Depends(get_db)) -> Tasks:
    task = TaskORM(title=payload.title, completed=False)
    db.add(task)
    db.commit()
    return task_to_model(task)


@app.patch("/tasks/{task_id}", response_model=Tasks, status_code=status.HTTP_200_OK)
def update_tasks(task_id: str, payload: TasksUpdate, db: Session = Depends(get_db)):
    """
    Обновить существующую задачу
    task_id получаем из url
    payload получаем из тела запроса
    """
    task = db.get(TaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task.title = payload.title if payload.title is not None else task.title
    task.completed = payload.completed if payload.completed is not None else task.completed
    db.commit()
    return task_to_model(task)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tasks(task_id: str, db: Session = Depends(get_db)) -> None:
    task = db.get(TaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")

    db.delete(task)
    db.commit()




categories: list[Categories] = []


class Categories(BaseModel):
    id: str
    name: str
    completed: bool

class CategoriesCreate(BaseModel):
    name: str

class CategoriesUpdate(BaseModel):
    name: str | None = None
    completed: bool | None = None


def categories_to_model(categories: CategoriesORM) -> Categories:
    return Categories(id=categories.id, name=categories.name, completed=categories.completed)



@app.get("/categories",response_model=list[Categories], status_code=status.HTTP_200_OK)
def get_categories(db: Categories = Depends(get_db)) -> list[Categories]:
    categories = db.scalars(select(CategoriesORM)).all()
    return [categories_to_model(category) for category in categories]


@app.post("/categories", status_code=status.HTTP_201_CREATED)
def create_categories(payload: CategoriesCreate, db: Session = Depends(get_db)) -> Categories:
    category = CategoriesORM(name=payload.name, completed=False)
    db.add(category)
    db.commit()
    return categories_to_model(category)



@app.patch("/categories/{categories_id}", status_code=status.HTTP_200_OK)
def update_categories(categories_id: str, payload: CategoriesUpdate, db: Session = Depends(get_db)):
    category = db.get(CategoriesORM, categories_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    category.name = payload.name if payload.name is not None else category.name
    category.completed = payload.completed if payload.completed is not None else category.completed
    db.commit()
    return categories_to_model(category)


@app.delete("/categories/{categories_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categories(categories_id: str, db: Session = Depends(get_db)):
    category = db.get(CategoriesORM, categories_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")

    db.delete(category)
    db.commit()




if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
