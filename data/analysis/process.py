from collections import OrderedDict
import pympi

from simplesvg import Scene, Line


############################################################################
#     Processing of the EAF file
############################################################################

elan_file = "../4.eaf"

tier = "Attention focus"
#tier = "Robot state"

eaf = pympi.Elan.Eaf(elan_file)

annotation2foa = {"Waiting for feedback": ("Tablet", "Secondary tablet", "Facilitator"),
        "Writing word": ("Tablet", "Robot"),
        "Waiting for word to write": ("Secondary tablet",),
        "Story telling": ("Robot",),
        "Presentation": ("Robot",),
        "robot": ("Robot",),
        "tablet": ("Tablet",),
        "facilitator": ("Facilitator",),
        "selection": ("Secondary tablet",),
        "observer": ("Observer",),
        "paper": ("Other",), # is that correct?
        "other": ("Other",)}


def get_time(ts):
    """ Returns the timestamp of an EAF 'timeslot', in seconds
    """
    return eaf.timeslots[ts] / 1000.


# First, convert all EAF timeslots into timestamp in seconds and 'normalize'
# the focus of attention using the mappings in annotation2foa
rawevents = {}
for _, entry in eaf.tiers[tier][0].items():
    ts, te, ann, _ = entry

    if ann not in annotation2foa:
        print("Unknown annotation: %s" % ann)
        continue

    rawevents[get_time(ts)] = (annotation2foa[ann], get_time(te))

# Order the 'events' by timestamps
events = OrderedDict(sorted(rawevents.items(), key=lambda t: t[0]))

############################################################################
#     SVG rendering
############################################################################

plotting_order = {"Observer": 0,
                  "Facilitator": 1,
                  "Secondary tablet": 2,
                  "Robot": 3,
                  "Tablet": 4,
                  "Other": 5}


svg = Scene(tier)

for ts, evt in events.items():

    targets, te = evt
    for t in targets:
        print("%s: %d to %d" % (t, ts, te))

        # a different offset for each 'target'
        offset = plotting_order[t] * 10

        # simply draw a plain line between the two timestamps
        svg.add(Line((ts, offset), (te,offset)))

svg.write_svg()
