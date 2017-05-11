from threading import Semaphore

from peewee import BooleanField, CharField, IntegerField, ForeignKeyField, Model, SqliteDatabase, \
    FloatField, TimestampField


db = SqliteDatabase('../data/LightSTM.db', threadlocals=True)
sem = Semaphore(1)


class BaseModel(Model):
    """A base model that will use our Sqlite database."""
    id = IntegerField(primary_key=True)

    @classmethod
    def get_or_none(cls, *query, **kwargs):
        try:
            return cls.get(*query)
        except cls.DoesNotExist:
            return None

    @classmethod
    def create(cls, *args, **kwargs):
        sem.acquire()
        try:
            instance = super().create(*args, **kwargs)
            sem.release()
            return instance
        except Exception:
            sem.release()
            raise Exception(
                'ERROR creating instance of class {} with attributes {}'.format(cls.__name__, args)
            )

    class Meta:
        database = db


class BusLine(BaseModel):
    bus = CharField()
    destination = CharField()
    going = BooleanField()
    variant_id = IntegerField(unique=True)

    def stops(self):
        return (sl.stop for sl in self.stop_lines.select())

    def __repr__(self):
        return '<BusLine {b.bus} to {b.destination} ({b.going})>'.format(b=self)


class BusStop(BaseModel):
    external_id = IntegerField(unique=True)
    latitude = CharField()
    longitude = CharField()
    name = CharField()

    def lines(self):
        return (sl.line for sl in self.stop_lines.select())

    def __repr__(self):
        return (
            '<BusStop {s.name} ({s.external_id}) at ({s.latitude}, {s.longitude})>'.format(s=self)
        )


class BusStopLine(BaseModel):
    line = ForeignKeyField(BusLine, related_name='stop_lines')
    stop = ForeignKeyField(BusStop, related_name='stop_lines')
    favorite = BooleanField()

    def __repr__(self):
        return '<BusStopLine {sl.line} and {sl.stop})>'.format(sl=self)


class BusLinePath(BaseModel):
    line = ForeignKeyField(BusLine, related_name='path', unique=True)
    sequence = IntegerField(unique=True)
    external_id = IntegerField()
    name = CharField()
    type = IntegerField()

    def __repr__(self):
        return '<BusLinePath {p.line.bus} #{p.sequence}: {p.name} ({p.external_id})>'.format(p=self)


class BusUnit(BaseModel):
    unit_id = IntegerField(unique=True)
    universal_access = BooleanField(default=False)

    def __repr__(self):
        return '<BusUnit {u.unit_id}>'.format(u=self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


class Log(BaseModel):
    line = ForeignKeyField(BusLine, related_name='logs')
    unit = ForeignKeyField(BusUnit, related_name='logs')

    expected_time = IntegerField()
    route_id = IntegerField()

    latitude = FloatField()
    longitude = FloatField()
    timestamp = TimestampField()

    def __repr__(self):
        return '<Log {l.unit} at ({l.latitude}, {l.longitude}) | {l.timestamp}>'.format(l=self)
