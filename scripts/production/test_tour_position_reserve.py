"""Projection reserves must not invalidate immutable, already legal positions."""
import copy
import math
import unittest

from tour_connection_motion import repair_positions_numpy


class EmptySpace:
    walls=[]
    leaves=[]
    furniture=[]
    radius=180

    def blocked(self,point):
        return False

    def line_free(self,start,end):
        return True


class PositionReserveTests(unittest.TestCase):
    def frozen_fixture(self,acceleration=3.0):
        # At 10fps, a 30mm second difference is exactly 3m/s². All
        # displacements remain well below the existing 1.2m/s speed ceiling.
        frames=[{'pointMm':[0.,0.]},{'pointMm':[0.,0.]},
                {'pointMm':[acceleration*10.,0.]}]
        tour={'fps':10,'frames':frames,'visits':[
            {'name':'start','frame':0},{'name':'end','frame':2}]}
        config={'chapters':[{'phase':'observe','from':'start','to':'end'}],
                'trajectoryPolicy':{'maximumPlanarAccelerationMps2':3.0}}
        return tour,config

    def test_zero_reserve_accepts_legal_frozen_acceleration_without_mutation(self):
        for acceleration in (2.99,3.0):
            with self.subTest(acceleration=acceleration):
                tour,config=self.frozen_fixture(acceleration)
                before=copy.deepcopy(tour)
                with self.assertRaisesRegex(ValueError,'Frozen observation movement'):
                    repair_positions_numpy(tour,config,EmptySpace())
                result,evidence=repair_positions_numpy(
                    tour,config,EmptySpace(),speed_headroom_fraction=0,
                    acceleration_headroom_fraction=0)
                self.assertTrue(evidence['accepted'])
                self.assertTrue(evidence['observationPositionsPreserved'])
                self.assertEqual(evidence['maximumDisplacementMm'],0)
                self.assertEqual(result,before)
                self.assertEqual(tour,before)

    def test_zero_reserve_does_not_waive_actual_acceleration_limit(self):
        tour,config=self.frozen_fixture(3.01)
        with self.assertRaisesRegex(ValueError,'Frozen observation movement'):
            repair_positions_numpy(tour,config,EmptySpace(),
                speed_headroom_fraction=0,acceleration_headroom_fraction=0)

    def test_zero_reserve_does_not_waive_actual_walking_limit(self):
        tour,config=self.frozen_fixture()
        for i,f in enumerate(tour['frames']):
            f['pointMm']=[125.*i,0.]
        with self.assertRaisesRegex(ValueError,'Frozen observation movement'):
            repair_positions_numpy(tour,config,EmptySpace(),
                speed_headroom_fraction=0,acceleration_headroom_fraction=0)

    def test_invalid_reserves_are_rejected(self):
        tour,config=self.frozen_fixture(1.0)
        for field in ('speed_headroom_fraction','acceleration_headroom_fraction'):
            for value in (-.001,.051,float('nan'),float('inf'),True,'0',None):
                with self.subTest(field=field,value=value):
                    with self.assertRaisesRegex(ValueError,'reserve must be finite'):
                        repair_positions_numpy(tour,config,EmptySpace(),**{field:value})

    def local_fixture(self):
        frames=[{'pointMm':[i*20.,0.]} for i in range(31)]
        frames[15]['pointMm'][1]=80.
        tour={'fps':24,'frames':frames,'visits':[
            {'name':'a','frame':0},{'name':'b','frame':9},
            {'name':'c','frame':21},{'name':'d','frame':30}]}
        config={'chapters':[
            {'phase':'observe','from':'a','to':'b'},
            {'phase':'transit','from':'b','to':'c'},
            {'phase':'observe','from':'c','to':'d'}]}
        return tour,config

    def test_local_free_interval_does_not_change_frozen_context(self):
        tour,config=self.local_fixture()
        before=copy.deepcopy(tour)
        result,evidence=repair_positions_numpy(tour,config,EmptySpace(),
            maximum_iterations=4000,speed_headroom_fraction=0,
            acceleration_headroom_fraction=0)
        self.assertTrue(evidence['accepted'])
        self.assertGreater(evidence['maximumDisplacementMm'],0)
        self.assertEqual(result['frames'][:10],before['frames'][:10])
        self.assertEqual(result['frames'][21:],before['frames'][21:])
        self.assertEqual(result['visits'],before['visits'])
        self.assertEqual(len(result['frames']),len(before['frames']))
        self.assertEqual(tour,before)

    def test_omitted_reserves_equal_unchanged_explicit_defaults(self):
        tour,config=self.local_fixture()
        default,first=repair_positions_numpy(tour,config,EmptySpace(),maximum_iterations=4000)
        explicit,second=repair_positions_numpy(tour,config,EmptySpace(),
            maximum_iterations=4000,speed_headroom_fraction=.001,
            acceleration_headroom_fraction=.02)
        self.assertEqual(default,explicit)
        self.assertEqual(first,second)

    def test_tolerance_may_only_tighten_default_precision(self):
        tour,config=self.local_fixture()
        for value in (1e-4,1.00001e-5,0,-1e-8,float('nan'),float('inf'),True,'1e-8',None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'tolerance may only tighten'):
                    repair_positions_numpy(tour,config,EmptySpace(),
                        projection_tolerance_mm=value)

    def test_tight_tolerance_certifies_residual_and_preserves_frozen_context(self):
        tour,config=self.local_fixture()
        before=copy.deepcopy(tour)
        result,evidence=repair_positions_numpy(tour,config,EmptySpace(),
            speed_headroom_fraction=0,acceleration_headroom_fraction=0,
            projection_tolerance_mm=1e-8)
        self.assertTrue(evidence['accepted'])
        self.assertLess(evidence['residualMm'],1e-8)
        self.assertEqual(evidence['projectionToleranceMm'],1e-8)
        self.assertEqual(result['frames'][:10],before['frames'][:10])
        self.assertEqual(result['frames'][21:],before['frames'][21:])
        self.assertEqual(result['visits'],before['visits'])
        self.assertEqual(tour,before)
        points=[f['pointMm'] for f in result['frames']]
        acceleration=max(math.hypot(*(z[k]-2*b[k]+a[k] for k in (0,1)))
                         *tour['fps']**2/1000
                         for a,b,z in zip(points,points[1:],points[2:]))
        self.assertLessEqual(acceleration,3.0+1e-8)


if __name__=='__main__':
    unittest.main()
