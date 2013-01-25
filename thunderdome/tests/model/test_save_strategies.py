import uuid
from thunderdome import connection 
from thunderdome.tests.base import BaseCassEngTestCase

from thunderdome.models import Edge, Vertex, SaveStrategyException
from thunderdome import columns


class OnceSaveStrategy(Vertex):
    """
    Should be enforced on vid
    """


class OnChangeSaveStrategy(Vertex):
    val = columns.Integer(save_strategy=columns.SAVE_ONCHANGE)


class AlwaysSaveStrategy(Vertex):
    val = columns.Integer(save_strategy=columns.SAVE_ALWAYS)


class ModelLevelSaveStrategy(Vertex):
    __default_save_strategy__ = columns.SAVE_ONCHANGE
    
    val = columns.Integer()


class DefaultModelLevelSaveStrategy(Vertex):
    val = columns.Integer()

    
class TestOnceSaveStrategy(BaseCassEngTestCase):

    def test_should_be_able_to_resave_with_once_strategy(self):
        """Once save strategy should allow saving so long as columns haven't changed'"""
        v = OnceSaveStrategy.create()
        assert 'vid' not in v.as_save_params()
        v.save()
        
    def test_should_enforce_once_save_strategy(self):
        """Should raise SaveStrategyException if once save strategy violated"""
        v = OnceSaveStrategy.create()
        v.vid = str(uuid.uuid4())

        with self.assertRaises(SaveStrategyException):
            v.save()

            
class TestOnChangeSaveStrategy(BaseCassEngTestCase):

    def test_should_be_able_to_save_columns_with_on_change(self):
        """Should be able to resave models with on change save policy"""
        v = OnChangeSaveStrategy.create(val=1)
        v.save()

    def test_should_persist_changes_with_on_change_strategy(self):
        """Should still persist changes with onchange save strategy"""
        v = OnChangeSaveStrategy.create(val=1)
        assert 'val' not in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()

        v1 = OnChangeSaveStrategy.get(v.vid)
        assert v1.val == 2

        
class TestAlwaysSaveStrategy(BaseCassEngTestCase):

    def test_should_be_able_to_save_with_always(self):
        """Should be able to save with always save strategy"""
        v = AlwaysSaveStrategy.create(val=1)
        assert 'val' in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()

        v1 = AlwaysSaveStrategy.get(v.vid)
        assert v1.val == 2


class TestModelLevelSaveStrategy(BaseCassEngTestCase):

    def test_default_save_strategy_should_be_always(self):
        """Default save strategy should be to always save"""
        v = DefaultModelLevelSaveStrategy.create(val=1)
        assert 'val' in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()
        
    def test_should_use_default_model_save_strategy(self):
        """Should use model-level save strategy if none provided"""
        v = ModelLevelSaveStrategy.create(val=1)
        assert 'val' not in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()
