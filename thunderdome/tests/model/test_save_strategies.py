# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import uuid
from thunderdome import connection 
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.models import Edge, Vertex, SaveStrategyException
from thunderdome import properties


class OnceSaveStrategy(Vertex):
    """
    Should be enforced on vid
    """


class OnChangeSaveStrategy(Vertex):
    val = properties.Integer(save_strategy=properties.SAVE_ONCHANGE)


class AlwaysSaveStrategy(Vertex):
    val = properties.Integer(save_strategy=properties.SAVE_ALWAYS)


class ModelLevelSaveStrategy(Vertex):
    __default_save_strategy__ = properties.SAVE_ONCHANGE
    
    val = properties.Integer()


class DefaultModelLevelSaveStrategy(Vertex):
    val = properties.Integer()

    
class TestOnceSaveStrategy(BaseThunderdomeTestCase):

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

            
class TestOnChangeSaveStrategy(BaseThunderdomeTestCase):

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

        
class TestAlwaysSaveStrategy(BaseThunderdomeTestCase):

    def test_should_be_able_to_save_with_always(self):
        """Should be able to save with always save strategy"""
        v = AlwaysSaveStrategy.create(val=1)
        assert 'val' in v.as_save_params()
        v.val = 2
        assert 'val' in v.as_save_params()
        v.save()

        v1 = AlwaysSaveStrategy.get(v.vid)
        assert v1.val == 2


class TestModelLevelSaveStrategy(BaseThunderdomeTestCase):

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
