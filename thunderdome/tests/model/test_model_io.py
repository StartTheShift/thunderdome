from unittest import skip
from thunderdome.tests.base import BaseCassEngTestCase

from thunderdome.management import create_table
from thunderdome.management import delete_table
from thunderdome.models import Vertex
from thunderdome import columns

class TestModel(Vertex):
    vid = columns.UUID()
    count   = columns.Integer()
    text    = columns.Text(required=False)

class TestModelIO(BaseCassEngTestCase):

    def test_model_save_and_load(self):
        """
        Tests that models can be saved and retrieved
        """
        tm0 = TestModel.create(count=8, text='123456789')
        tm1 = TestModel.create(count=9, text='456789')
        tms = TestModel.all([tm0.vid, tm1.vid])

        assert len(tms) == 2
       
        for cname in tm0._columns.keys():
            self.assertEquals(getattr(tm0, cname), getattr(tms[0], cname))
            
        tms = TestModel.all([tm1.vid, tm0.vid])
        assert tms[0].vid == tm1.vid 
        assert tms[1].vid == tm0.vid 
            
    def test_model_updating_works_properly(self):
        """
        Tests that subsequent saves after initial model creation work
        """
        tm = TestModel.create(count=8, text='123456789')

        tm.count = 100
        tm.save()

        tm.count = 80
        tm.save()

        tm.count = 60
        tm.save()

        tm.count = 40
        tm.save()

        tm.count = 20
        tm.save()

        tm2 = TestModel.get(tm.vid)
        self.assertEquals(tm.count, tm2.count)

    def test_model_deleting_works_properly(self):
        """
        Tests that an instance's delete method deletes the instance
        """
        import ipdb; ipdb.set_trace()
        tm = TestModel.create(count=8, text='123456789')
        eid = tm.eid
        tm.delete()
        with self.assertRaises(TestModel.DoesNotExist):
            tm2 = TestModel.get(eid)



