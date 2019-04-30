"""
NURBS and Bezier tools by Zak @ https://github.com/open3dengineering/i3_Berlin

See original script for usage examples:
https://github.com/open3dengineering/i3_Berlin/blob/master/Blender/python/curve_tools.py
"""

# #####BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# #####END GPL LICENSE BLOCK #####


import bpy
from mathutils import *
from bpy.props import *



### GENERAL CURVE FUNCTIONS

#distance between 2 points
def dist(p1, p2):
    return (p2-p1).magnitude

#sets cursors position for debugging porpuses
def cursor(pos):
    bpy.context.scene.cursor_location = pos

#cuadratic bezier value
def quad(p, t):
    return p[0]*(1.0-t)**2.0 + 2.0*t*p[1]*(1.0-t) + p[2]*t**2.0

#cubic bezier value
def cubic(p, t):
    return p[0]*(1.0-t)**3.0 + 3.0*p[1]*t*(1.0-t)**2.0 + 3.0*p[2]*(t**2.0)*(1.0-t) + p[3]*t**3.0

#gets a bezier segment's control points on global coordinates
def getbezpoints(spl, mt, seg=0):
    points = spl.bezier_points
    p0 = mt * points[seg].co
    p1 = mt * points[seg].handle_right
    p2 = mt * points[seg+1].handle_left
    p3 = mt * points[seg+1].co
    return p0, p1, p2, p3

#gets nurbs polygon control points on global coordinates
def getnurbspoints(spl, mw):
    pts = []
    ws = []
    for p in spl.points:
        v = Vector(p.co[0:3])*mw
        pts.append(v)
        ws.append(p.weight)
    return pts , ws

#calcs a nurbs knot vector
def knots(n, order, type=0):#0 uniform 1 endpoints 2 bezier

    kv = []

    t = n+order
    if type==0:
        for i in range(0, t):
            kv.append(1.0*i)

    elif type==1:
        k=0.0
        for i in range(1, t+1):
            kv.append(k)
            if i>=order and i<=n:
                k+=1.0
    elif type==2:
        if order==4:
            k=0.34
            for a in range(0,t):
                if a>=order and a<=n: k+=0.5
                kv.append(floor(k))
                k+=1.0/3.0

        elif order==3:
            k=0.6
            for a in range(0, t):
                if a >=order and a<=n: k+=0.5
                kv.append(floor(k))

    ##normalize the knot vector
    for i in range(0, len(kv)):
        kv[i]=kv[i]/kv[-1]

    return kv

#nurbs curve evaluation
def C(t, order, points, weights, knots):
    #c = Point([0,0,0])
    c = Vector()
    rational = 0
    i = 0
    while i < len(points):
        b = B(i, order, t, knots)
        p = points[i] * (b * weights[i])
        c = c + p
        rational = rational + b*weights[i]
        i = i + 1

    return c * (1.0/rational)

#nurbs basis function
def B(i,k,t,knots):
    ret = 0
    if k>0:
        n1 = (t-knots[i])*B(i,k-1,t,knots)
        d1 = knots[i+k] - knots[i]
        n2 = (knots[i+k+1] - t) * B(i+1,k-1,t,knots)
        d2 = knots[i+k+1] - knots[i+1]
        if d1 > 0.0001 or d1 < -0.0001:
            a = n1 / d1
        else:
            a = 0
        if d2 > 0.0001 or d2 < -0.0001:
            b = n2 / d2
        else:
            b = 0
        ret = a + b
        #print "B i = %d, k = %d, ret = %g, a = %g, b = %g\n"%(i,k,ret,a,b)
    else:
        if knots[i] <= t and t <= knots[i+1]:
            ret = 1
        else:
            ret = 0
    return ret

#calculates a global parameter t along all control points
#t=0 begining of the curve
#t=1 ending of the curve

def calct(obj, t, local=False):
    """
    @param  local : bool
            Use local coordinates rather than world coordinates
    """

    spl=None
    if local:
        mw = Matrix.Identity(4)
    else:
        mw = obj.matrix_world
    
    if obj.data.splines.active==None:
        if len(obj.data.splines)>0:
            spl=obj.data.splines[0]
    else:
        spl = obj.data.splines.active

    if spl==None:
        return False

    if spl.type=="BEZIER":
        points = spl.bezier_points
        nsegs = len(points)-1

        d = 1.0/nsegs
        seg = int(t/d)
        t1 = t/d - int(t/d)

        if t==1:
            seg-=1
            t1 = 1.0

        p = getbezpoints(spl,mw, seg)

        coord = cubic(p, t1)

        return coord

    elif spl.type=="NURBS":
        data = getnurbspoints(spl, mw)
        pts = data[0]
        ws = data[1]
        order = spl.order_u
        n = len(pts)
        ctype = spl.use_endpoint_u
        kv = knots(n, order, ctype)

        coord = C(t, order-1, pts, ws, kv)

        return coord

#length of the curve
def arclength(obj):
    if obj.type != 'CURVE':
        raise ValueError(obj.type)
    
    prec = 1000 #precision
    inc = 1/prec #increments

    ### TODO: set a custom precision value depending the number of curve points
    #that way it can gain on accuracy in less operations.

    #subdivide the curve in 1000 lines and sum its magnitudes
    length = 0.0
    for i in range(0, prec):
        ti = i*inc
        tf = (i+1)*inc
        a = calct(obj, ti)
        b = calct(obj, tf)
        r = (b-a).magnitude
        length += r

    return length



### LOFT INTERPOLATIONS

#objs = selected objects
#i = object index
#t = parameter along u direction
#tr = parameter along v direction

#linear
def intl(objs, i, t, tr):
    p1 = calct(objs[i],t)
    p2 = calct(objs[i+1], t)

    r = p1 + (p2 - p1)*tr

    return r

#tipo = interpolation type
#tension and bias are for hermite interpolation
#they can be changed to obtain different lofts.

#cubic
def intc(objs, i, t, tr, tipo=3, tension=0.0, bias=0.0):

    ncurves =len(objs)

    #if 2 curves go to linear interpolation regardless the one you choose
    if ncurves<3:
        return intl(objs, i, t, tr)
    else:

        #calculates the points to be interpolated on each curve
        if i==0:
            p0 = calct(objs[i], t)
            p1 = p0
            p2 = calct(objs[i+1], t)
            p3 = calct(objs[i+2], t)
        else:
            if ncurves-2 == i:
                p0 = calct(objs[i-1], t)
                p1 = calct(objs[i], t)
                p2 = calct(objs[i+1], t)
                p3 = p2
            else:
                p0 = calct(objs[i-1], t)
                p1 = calct(objs[i], t)
                p2 = calct(objs[i+1], t)
                p3 = calct(objs[i+2], t)


    #calculates the interpolation between those points
    #i used methods from this page: http://paulbourke.net/miscellaneous/interpolation/

    if tipo==0:
        #linear
        return intl(objs, i, t, tr)
    elif tipo == 1:
        #natural cubic
        t2 = tr*tr
        a0 = p3-p2-p0+p1
        a1 = p0-p1-a0
        a2 = p2-p0
        a3 = p1
        return a0*tr*t2 + a1*t2+a2*tr+a3
    elif tipo == 2:
        #catmull it seems to be working. ill leave it for now.
        t2 = tr*tr
        a0 = -0.5*p0 +1.5*p1 -1.5*p2 +0.5*p3
        a1 = p0 - 2.5*p1 + 2*p2 -0.5*p3
        a2 = -0.5*p0 + 0.5 *p2
        a3 = p1
        return a0*tr*tr + a1*t2+a2*tr+a3

    elif tipo == 3:
        #hermite
        tr2 = tr*tr
        tr3 = tr2*tr
        m0 = (p1-p0)*(1+bias)*(1-tension)/2
        m0+= (p2-p1)*(1-bias)*(1-tension)/2
        m1 = (p2-p1)*(1+bias)*(1-tension)/2
        m1+= (p3-p2)*(1-bias)*(1-tension)/2
        a0 = 2*tr3 - 3*tr2 + 1
        a1 = tr3 - 2 * tr2+ tr
        a2 = tr3 - tr2
        a3 = -2*tr3 + 3*tr2

        return a0*p1+a1*m0+a2*m1+a3*p2



#derives a curve at a given parameter
def deriv(curve, t, unit=False):

    a = t + 0.001
    if t==1: a=t-0.001

    pos = calct(curve, t)
    der = (pos-calct(curve, a))/(t-a)
    if unit:
        der = der/der.magnitude
    return der


#reads spline points
#spl spline to read
#rev reads the spline forward or backwards
def readspline(spl, rev=0):
    res = []

    if spl.type=="BEZIER":
        points = spl.bezier_points
        for p in points:
            if rev:
                h2 = p.handle_left
                h1 = p.handle_right
                h2type = p.handle_left_type
                h1type = p.handle_right_type
            else:
                h1 = p.handle_left
                h2 = p.handle_right
                h1type = p.handle_left_type
                h2type = p.handle_right_type

            co = p.co
            res.append([h1, co, h2, h1type, h2type])
    if rev:
        res.reverse()

    return res

#returns a new merged spline
#cu curve object
#pts1 points from the first spline
#pts2 points from the second spline

def merge(cu, pts1, pts2):
    newspl = cu.data.splines.new(type="BEZIER")
    for i, p in enumerate(pts1):

        if i>0: newspl.bezier_points.add()
        newspl.bezier_points[i].handle_left = p[0]
        newspl.bezier_points[i].co = p[1]
        newspl.bezier_points[i].handle_right = p[2]
        newspl.bezier_points[i].handle_left_type = p[3]
        newspl.bezier_points[i].handle_right_type = p[4]

    newspl.bezier_points[-1].handle_right_type="FREE"
    newspl.bezier_points[-1].handle_left_type="FREE"

    newspl.bezier_points[-1].handle_right = pts2[0][2]


    for j in range(1, len(pts2)):

        newspl.bezier_points.add()
        newspl.bezier_points[-1].handle_left = pts2[j][0]
        newspl.bezier_points[-1].co = pts2[j][1]
        newspl.bezier_points[-1].handle_right = pts2[j][2]
        newspl.bezier_points[-1].handle_left_type = pts2[j][3]
        newspl.bezier_points[-1].handle_right_type = pts2[j][4]

    return newspl

