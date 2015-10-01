from collections import OrderedDict
import pympi

from simplesvg import Scene, Line, Polyline



############################################################################
#     Processing of the EAF file
############################################################################

tier_groundtruth = "Attention focus"
tier_expected = "Robot state"


LOST = "Lost track"
OTHER = "Other"

annotation2foa = {
        ##### Robot state #####
        "Waiting for feedback": ("Tablet", "Secondary tablet"),
        "Writing word": ("Tablet", "Robot"),
        "Waiting for word to write": ("Secondary tablet",),
        "Story telling": ("Robot",),
        "Presentation": ("Robot",),
        "Bye": ("Robot",),
        ##### Attention focus #####
        "robot": ("Robot",),
        "tablet": ("Tablet",),
        "facilitator": ("Facilitator",),
        "selection": ("Secondary tablet",),
        "observer": ("Observer",),
        "paper": ("Secondary tablet",), 
        "other": ("Other",),
        "lost_track": (LOST,)}


def get_time(eaf, ts):
    """ Returns the timestamp of an EAF 'timeslot', in seconds
    """
    return eaf.timeslots[ts] / 1000.


# First, convert all EAF timeslots into timestamp in seconds and 'normalize'
# the focus of attention using the mappings in annotation2foa
def prepare(eaf, tier):
    rawevents = {}
    for _, entry in eaf.tiers[tier][0].items():
        ts, te, ann, _ = entry

        if ann not in annotation2foa:
            print("Unknown annotation: %s" % ann)
            continue

        rawevents[get_time(eaf, ts)] = (annotation2foa[ann], get_time(eaf, te))

    # Order the 'events' by timestamps
    return OrderedDict(sorted(rawevents.items(), key=lambda t: t[0]))

############################################################################
#     CSV files
############################################################################


def parse_robot_observations(robot_observations_file):

    events_observed = OrderedDict()

    with open(robot_observations_file,'r') as observations:
        t_start = 0
        current_target = None
        last_t = 0
        for l in observations.readlines():
            a, target = l.split(":")
            t_data = int(a)
            target = target.strip()

            if target not in annotation2foa:
                print("Unknown annotation: %s" % target)
                continue


            if last_t != 0 and t_data != last_t+1:
                events_observed[t_start*0.1] = (annotation2foa[current_target],(last_t+1)*0.1)
                events_observed[(last_t+1)*0.1] = (annotation2foa['other'],t_data*0.1)
                t_start = t_data
            else:
                if current_target is not None and target != current_target:
                    events_observed[t_start*0.1] = (annotation2foa[current_target],(last_t+1)*0.1)
                    t_start = t_data
            
            current_target = target
            last_t = t_data

    return events_observed

def filter_observations(obs, min_duration):

    filtered = {}

    for idx, k in enumerate(obs.keys()):
        if obs[k][1] - k < min_duration and \
           obs[k][0] == ("Other",):
            filtered[k] = (obs[obs.keys()[idx-1]][0], obs[k][1])
        else:
            filtered[k] = obs[k]

    filtered = OrderedDict(sorted(filtered.items(), key=lambda t: t[0]))
    return filtered

############################################################################
#     SVG rendering
############################################################################

plotting_order = {"Observer": 6,
                  "Facilitator": 5,
                  "Secondary tablet": 4,
                  "Robot": 3,
                  "Tablet": 2,
                  "Other": 1,
                  "Lost track": 0}


def plot(name, events):
    svg = Scene(name)

    for ts, evt in events.items():

        targets, te = evt
        for t in targets:
            #print("%s: %d to %d" % (t, ts, te))

            # a different offset for each 'target'
            offset = plotting_order[t] * 10

            # simply draw a plain line between the two timestamps
            svg.add(Line((ts, offset), (te,offset)))

    svg.write_svg()

############################################################################
#     With-me-ness
############################################################################

from numpy import arange

dt = 0.1 # seconds


def find_interval(t, intervals):
    for ts, te, target in intervals:
        if ts <= t and te >= t:
            return ts, te, target
    return None, None, None

def withmeness(observations, expectations, name = None, t_start = None, t_end = None):

    if t_end is None:
        t_end = observations[observations.keys()[-1]][1]
    else:
        t_end = min(t_end, observations[observations.keys()[-1]][1])


    if t_start is None:
        t_start = 0

    total_time = 0.
    total_time_matching = 0.

    observations_intervals = [(k, v[1], v[0]) for k,v in observations.items()]
    expectations_intervals = [(k, v[1], v[0]) for k,v in expectations.items()]

    csv = None
    if name:
        csv = open(name + ".csv", "w")
        csv.write("t,rating1,rating2\n")

    for t in arange(t_start, t_end, dt):

            expected_start, _, e_target = find_interval(t, expectations_intervals)
            observations_start, _, o_target = find_interval(t, observations_intervals)

            if e_target and o_target:
                target = observations[observations_start][0][0]

                if target != LOST and target != OTHER:
                    if csv:
                        csv.write("%s,%s,%s\n" % (t, '/'.join(e_target), '/'.join(o_target)))

                    total_time += dt

                    expected_targets = expectations[expected_start][0]

                    if target in expected_targets:
                        total_time_matching += dt

    if csv:
        csv.close()

    if total_time == 0:
        import pdb;pdb.set_trace()
        return None

    withmeness = total_time_matching/total_time
    print("Total time: %s sec, total time matching: %s sec, With-me-ness: %s" % (total_time, total_time_matching, withmeness))

    return withmeness

def plot_withmeness(name, observations, expectations, sliding_window = 30):
    svg = Scene(name)

    t_end = observations[observations.keys()[-1]][1]

    points = []

    delta = 1
    #delta = sliding_window

    for t_start in arange(0, t_end-sliding_window+1, delta):

            w = withmeness(observations, expectations, name = None, t_start=t_start, t_end=(t_start + sliding_window))
            #print("start: %s, end: %s -> %s" % (t_start, t_start + sliding_window, w))

            if w is not None:
                points.append((t_start,-(w * 100)))
                #points.append((t_start + delta,-(w * 100)))


    svg.add(Polyline(points))
    svg.write_svg()



###############################################################################
total_duration = 0

for i in range(1,7):

    print("\n\nSubject %s\n" % i)
    path = "subject_%s/" % i
    elan_file = path + "webcam_%s.eaf" % i
    eaf = pympi.Elan.Eaf(elan_file)

    events_groundtruth = prepare(eaf, tier_groundtruth)
    events_expected = prepare(eaf, tier_expected)
    total_duration += events_expected[events_expected.keys()[-1]][1]

    elan_file_2nd_annotator = path + "webcam_%s_2.eaf" % i
    eaf_2nd = pympi.Elan.Eaf(elan_file_2nd_annotator)
    events_groundtruth_2nd = prepare(eaf_2nd, tier_groundtruth)

    robot_observations_file = path + "capturedFoA.csv"
    events_observed = parse_robot_observations(robot_observations_file)

    events_observed = filter_observations(events_observed, min_duration=0.5)


    #plot(path + "expected", events_expected)
    #plot(path + "groundtruth", events_groundtruth)
    #plot(path + "observed", events_observed)

    #print("With-me-ness groundtruth/expected")
    #withmeness(events_groundtruth, events_expected, path + "gt-expect")
    #print("---------------------------------")
    #plot_withmeness(path + "w-gt", events_groundtruth, events_expected)


    #print("=================================")
    #print("With-me-ness observed/expected")
    #withmeness(events_observed, events_expected, path + "obs-expect")
    #print("---------------------------------")
    #plot_withmeness(path + "w-obs", events_observed, events_expected)


    #print("=================================")
    #print("With-me-ness observed/groundtruth")
    #withmeness(events_observed, events_groundtruth, path + "obs-gt")

    print("=================================")
    print("Agreement annotators")
    withmeness(events_groundtruth_2nd, events_groundtruth, path + "annotators")


print("=================================")
print("Total: %dmin %dsec (per subject: %dmin %dsec)" % (total_duration // 60, total_duration % 60, (total_duration/6)//60, (total_duration/6) % 60))
print("Total: %smin (per subject: %smin)" % (total_duration / 60, (total_duration/6)/60))


