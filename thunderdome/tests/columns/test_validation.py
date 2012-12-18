#tests the behavior of the column classes
from datetime import datetime
from decimal import Decimal as D

from thunderdome.tests.base import BaseCassEngTestCase

from thunderdome.columns import Column
from thunderdome.columns import Bytes
from thunderdome.columns import Ascii
from thunderdome.columns import Text
from thunderdome.columns import Integer
from thunderdome.columns import DateTime
from thunderdome.columns import UUID
from thunderdome.columns import Boolean
from thunderdome.columns import Float
from thunderdome.columns import Decimal

from thunderdome.models import Vertex

class DatetimeTest(Vertex):
    test_id = Integer(primary_key=True)
    created_at = DateTime()
    
class TestDatetime(BaseCassEngTestCase):

    def test_datetime_io(self):
        now = datetime.now()
        dt = DatetimeTest.create(test_id=0, created_at=now)
        dt2 = DatetimeTest.get(dt.vid)
        assert dt2.created_at.timetuple()[:6] == now.timetuple()[:6]

class DecimalTest(Vertex):
    test_id = Integer(primary_key=True)
    dec_val = Decimal()
    
class TestDecimal(BaseCassEngTestCase):

    def test_datetime_io(self):
        dt = DecimalTest.create(test_id=0, dec_val=D('0.00'))
        dt2 = DecimalTest.get(dt.vid)
        assert dt2.dec_val == dt.dec_val

        dt = DecimalTest.create(test_id=0, dec_val=5)
        dt2 = DecimalTest.get(dt.vid)
        assert dt2.dec_val == D('5')
        












