import unittest
from tour_pipeline import rank

class RankTests(unittest.TestCase):
    def report(self,*codes):return {'issues':[{'code':c} for c in codes],'checks':{}}
    def test_a_numeric_angular_acceleration_breach_outranks_any_number_of_screen_issues(self):
        breach=rank(self.report('camera_angular_acceleration'),{'seconds':60})
        screens=rank(self.report(*['screen_near_surface_occlusion']*6),{'seconds':60})
        self.assertGreater(breach,screens)  # a larger tuple is a worse candidate: a numeric limit is a hard gate, screen issues are not
    def test_more_hard_breaches_rank_worse(self):
        one=rank(self.report('camera_angular_acceleration'),{'seconds':60});two=rank(self.report('camera_angular_acceleration','body_path_collision'),{'seconds':60})
        self.assertGreater(two,one)

if __name__=='__main__':unittest.main()
