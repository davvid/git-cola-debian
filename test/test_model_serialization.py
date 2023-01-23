#!/usr/bin/env python
import os
import unittest

import testlib
from testlib import InnerModel
from testlib import NestedModel

from cola.model import Model

class TestSaveRestore(unittest.TestCase):
    def setUp(self):
        testlib.create_test_dir()

        self.nested = NestedModel()
        path = os.path.join(testlib.get_test_dir(), 'test.data')
        # save & reconstitute
        self.nested.save(path)
        self.clone = Model.instance(path)

    def tearDown(self):
        testdir = testlib.get_test_dir()
        if os.path.exists(testdir):
            testlib.remove_test_dir()

    def testCloneToClass(self):
        self.failUnless( str(NestedModel) ==
                         str(self.clone.__class__) )

    def testClonedInnerToClass(self):
        self.failUnless( str(InnerModel) ==
                         str(self.clone.inner.__class__) )

    def testClonedListAndParam(self):
        self.failUnless( str(self.clone.inner.__class__) ==
                         str(self.clone.innerList[0].__class__) )

    def testList(self):
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerList[1][0].__class__) )

    def testListInList(self):
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerList[2][0][0].__class__))

    def testListInListInList(self):
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerList[3][0][0][0].__class__))

    def testDictInList(self):
        self.failUnless( str(dict) ==
                         str(self.clone.innerList[4].__class__))

    def testObjectInDictInList(self):
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerList[-1]["foo"].__class__))

if __name__ == '__main__':
    unittest.main()
