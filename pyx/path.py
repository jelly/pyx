#!/usr/bin/env python
#
#
# Copyright (C) 2002 J�rg Lehmann <joergl@users.sourceforge.net>
# Copyright (C) 2002 Andr� Wobst <wobsta@users.sourceforge.net>
#
# This file is part of PyX (http://pyx.sourceforge.net/).
#
# PyX is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# PyX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyX; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# TODO: - reversepath ?
#       - strokepath ?
#       - nocurrentpoint exception?
#       - implement bbox and ConvertToBezier for arct
#       - correct bbox for curveto
#       - intersection of bpaths

import unit, canvas
from math import floor, cos, sin, pi
from canvas import bbox


class PathException(Exception): pass

# 
# pathel: element of a PS style path 
#

class pathel:

    ' element of a PS style path '
    
    def bbox(self, canvas, currentpoint, currentsubpath):
	''' return bounding box of pathel 
	
	Important note: all coordinates in bbox, currentpoint, and 
	currrentsubpath have to be converted to pts.
	'''
	# Though conceptually a little ugly, this conversion is nevertheless
	# necessary, since one can, for instance, not compare two lengths 
	# without specifying canvas.unit.
	pass

    def write(self, canvas, file):
	' write pathel to file in the context of canvas '
        pass
	
    def ConvertToBezier(self, currentpoint, currentsubpath):
	' convert pathel to bpath '
        pass


class closepath(pathel): 
    ' Connect subpath back to its starting point '

    def bbox(self, canvas, currentpoint, currentsubpath):
	return (None,
                None, 
		bbox(min(currentpoint[0], currentsubpath[0]), 
  	             min(currentpoint[1], currentsubpath[1]), 
	             max(currentpoint[0], currentsubpath[0]), 
	             max(currentpoint[1], currentsubpath[1])))

    def write(self, canvas, file):
        file.write("closepath")

    def ConvertToBezier(self, currentpoint, currentsubpath):
        return (None,
                None,
                bline(currentpoint[0], currentpoint[1], 
                       currentsubpath[0], currentsubpath[1]))
 
 
class moveto(pathel):
    ' Set current point to (x, y) '

    def __init__(self, x, y):
         self.x = x
         self.y = y

    def bbox(self, canvas, currentpoint, currentsubpath):
	x=canvas.unit.pt(self.x)
	y=canvas.unit.pt(self.y)
        return ((x, y), (x, y) , bbox())
	 
    def write(self, canvas, file):
        file.write("%f %f moveto" % (canvas.unit.pt(self.x), canvas.unit.pt(self.y) ) )

    def ConvertToBezier(self, currentpoint, currentsubpath):
        return ((self.x, self.y), (self.x, self.y) , None)


class rmoveto(pathel):
    ' Perform relative moveto '

    def __init__(self, dx, dy):
         self.dx = dx
         self.dy = dy
        
    def bbox(self, canvas, currentpoint, currentsubpath):
	dx=canvas.unit.pt(self.dx)
	dy=canvas.unit.pt(self.dy)
        return ((dx+currentpoint[0], dy+currentpoint[1]), 
                (dx+currentpoint[0], dy+currentpoint[1]),
		bbox())

    def write(self, canvas, file):
        file.write("%f %f rmoveto" % (canvas.unit.pt(self.dx), canvas.unit.pt(self.dy) ) )
        
    def ConvertToBezier(self, currentpoint, currentsubpath):
        return ((self.dx+currentpoint[0], self.dy+currentpoint[1]), 
                (self.dx+currentpoint[0], self.dy+currentpoint[1]),
		None)


class lineto(pathel):
    ' Append straight line to (x, y) '

    def __init__(self, x, y):
         self.x = x
         self.y = y
	 
    def bbox(self, canvas, currentpoint, currentsubpath):
	x=canvas.unit.pt(self.x)
	y=canvas.unit.pt(self.y)
        return ((x, y),
                currentsubpath or currentpoint,
                bbox(min(currentpoint[0], x), min(currentpoint[1], y), 
		     max(currentpoint[0], x), max(currentpoint[1], y)))

    def write(self, canvas, file):
        file.write("%f %f lineto" % (canvas.unit.pt(self.x), canvas.unit.pt(self.y) ) )
       
    def ConvertToBezier(self, currentpoint, currentsubpath):
        return ((self.x, self.y), 
                currentsubpath or currentpoint,
                bline(currentpoint[0], currentpoint[1], self.x, self.y))


class rlineto(pathel):
    ' Perform relative lineto '

    def __init__(self, dx, dy):
         self.dx = dx
         self.dy = dy

    def bbox(self, canvas, currentpoint, currentsubpath):
	dx=canvas.unit.pt(self.dx)
	dy=canvas.unit.pt(self.dy)
        return ((currentpoint[0]+dx, currentpoint[1]+dy),
                currentsubpath or currentpoint,
                bbox(min(currentpoint[0], currentpoint[0]+dx),
		     min(currentpoint[1], currentpoint[1]+dy), 
	 	     max(currentpoint[0], currentpoint[0]+dx),
		     max(currentpoint[1], currentpoint[1]+dy)))

    def write(self, canvas, file):
        file.write("%f %f rlineto" % (canvas.unit.pt(self.dx), 
	                              canvas.unit.pt(self.dy)))
        
    def ConvertToBezier(self, currentpoint, currentsubpath):
        return ((currentpoint[0]+self.dx, currentpoint[1]+self.dy), 
                currentsubpath or currentpoint,
                bline(currentpoint[0], currentpoint[1], 
                      currentpoint[0]+self.dx, currentpoint[1]+self.dy))


class arc(pathel):
    ' Append counterclockwise arc '

    def __init__(self, x, y, r, angle1, angle2):
        self.x = x
        self.y = y
        self.r = r
	self.angle1 = angle1
	self.angle2 = angle2

    def bbox(self, canvas, currentpoint, currentsubpath):
        phi1=pi*self.angle1/180
        phi2=pi*self.angle2/180
	
	# starting point of arc segment
	sarcx = canvas.unit.pt(self.x+self.r*cos(phi1))
	sarcy = canvas.unit.pt(self.y+self.r*sin(phi1))

	# end point of arc segment
	earcx = canvas.unit.pt(self.x+self.r*cos(phi2))
	earcy = canvas.unit.pt(self.y+self.r*sin(phi2))

	# Now, we have to determine the corners of the bbox for the
	# arc segment, i.e. global maxima/mimima of cos(phi) and sin(phi)
	# in the interval [phi1, phi2]. These can either be located
	# on the borders of this interval or in the interior.

        if phi2<phi1:        
	    # guarantee that phi2>phi1
	    phi2 = phi2 + (floor((phi1-phi2)/(2*pi))+1)*2*pi

	# next minimum of cos(phi) looking from phi1 in counterclockwise 
	# direction: 2*pi*floor((phi1-pi)/(2*pi)) + 3*pi

	if phi2<(2*floor((phi1-pi)/(2*pi))+3)*pi:
	    minarcx = min(sarcx, earcx)
	else:
            minarcx = canvas.unit.pt(self.x-self.r)

	# next minimum of sin(phi) looking from phi1 in counterclockwise 
	# direction: 2*pi*floor((phi1-3*pi/2)/(2*pi)) + 7/2*pi

	if phi2<(2*floor((phi1-3*pi/2)/(2*pi))+7.0/2)*pi:
	    minarcy = min(sarcy, earcy)
	else:
            minarcy = canvas.unit.pt(self.y-self.r)

	# next maximum of cos(phi) looking from phi1 in counterclockwise 
	# direction: 2*pi*floor((phi1)/(2*pi))+2*pi

	if phi2<(2*floor((phi1)/(2*pi))+2)*pi:
	    maxarcx = max(sarcx, earcx)
	else:
            maxarcx = canvas.unit.pt(self.x+self.r)

	# next maximum of sin(phi) looking from phi1 in counterclockwise 
	# direction: 2*pi*floor((phi1-pi/2)/(2*pi)) + 1/2*pi

	if phi2<(2*floor((phi1-pi/2)/(2*pi))+5.0/2)*pi:
	    maxarcy = max(sarcy, earcy)
	else:
            maxarcy = canvas.unit.pt(self.y+self.r)

	# Finally, we are able to construct the bbox for the arc segment.
	# Note, that if there is a currentpoint defined, we also
	# have to include the straight line from this point
	# to the first point of the arc segment

	if currentpoint:
             return ( (earcx, earcy),
                      currentsubpath or currentpoint,
                      bbox(min(currentpoint[0], sarcx),
		                  min(currentpoint[1], sarcy), 
			          max(currentpoint[0], sarcx),
			          max(currentpoint[1], sarcy))+
	              bbox(minarcx, minarcy, maxarcx, maxarcy)
                    )
        else:  # we assert that currentsubpath is also None
             return ( (earcx, earcy),
                      (sarcx, sarcy),
	              bbox(minarcx, minarcy, maxarcx, maxarcy)
                    )

			    
    def write(self, canvas, file):
        file.write("%f %f %f %f %f arc" % ( canvas.unit.pt(self.x),
                                            canvas.unit.pt(self.y),
                                            canvas.unit.pt(self.r),
                                            self.angle1,
                                            self.angle2 ) )
        
    def ConvertToBezier(self, currentpoint, currentsubpath):
	# starting point of arc segment
	sarcx = self.x+self.r*cos(pi*self.angle1/180)
	sarcy = self.y+self.r*sin(pi*self.angle1/180)

	# end point of arc segment
	earcx = self.x+self.r*cos(pi*self.angle2/180)
	earcy = self.y+self.r*sin(pi*self.angle2/180)
        if currentpoint:
             return ( (earcx, earcy),
                      currentsubpath or currentpoint,
                      bline(currentpoint[0], currentpoint[1], sarcx, sarcy) +
                      barc(self.x, self.y, self.r, self.angle1, self.angle2)
                    )
        else:  # we assert that currentsubpath is also None
             return ( (earcx, earcy),
                      (sarcx, sarcy),
                      barc(self.x, self.y, self.r, self.angle1, self.angle2)
                    )
	
class arcn(pathel):
    ' Append clockwise arc '
    
    def __init__(self, x, y, r, angle1, angle2):
        self.x = x
        self.y = y
        self.r = r
	self.angle1 = angle1
	self.angle2 = angle2

    def bbox(self, canvas, currentpoint, currentsubpath):
        return arc(self.x, self.y, 
                   self.r, 
		   self.angle2, self.angle1).bbox(currentpoint,currentsubpath)

    def write(self, canvas, file):
        file.write("%f %f %f %f %f arcn" % ( canvas.unit.pt(self.x),
                                             canvas.unit.pt(self.y),
                                             canvas.unit.pt(self.r),
                                             self.angle1,
                                             self.angle2 ) )

    def ConvertToBezier(self, currentpoint, currentsubpath):
        return arc(self.x, self.y, 
                   self.r, 
		   self.angle2, self.angle1).ConvertToBezier(currentpoint,currentsubpath)

class arct(pathel):
    ' Append tangent arc '

    def __init__(self, x1, y1, x2, y2, r):
        self.x1 = x1
	self.y1 = y1
	self.x2 = x2
	self.y2 = y2
	self.r = r

    def write(self, canvas, file):
        file.write("%f %f %f %f %f arct" % ( canvas.unit.pt(self.x1),
                                             canvas.unit.pt(self.y1),
                                             canvas.unit.pt(self.x2),
                                             canvas.unit.pt(self.y2),
                                             canvas.unit.pt(self.r) ) )
        
	
class curveto(pathel):

    def __init__(self, x1, y1, x2, y2, x3, y3):
        self.x1 = x1
	self.y1 = y1
	self.x2 = x2
	self.y2 = y2
	self.x3 = x3
	self.y3 = y3
	
    def bbox(self, canvas, currentpoint, currentsubpath):
	x1=canvas.unit.pt(self.x1)
	y1=canvas.unit.pt(self.y1)
	x2=canvas.unit.pt(self.x2)
	y2=canvas.unit.pt(self.y2)
	x3=canvas.unit.pt(self.x3)
	y3=canvas.unit.pt(self.y3)
        return ((x3, y3),
                currentsubpath or currentpoint,
                bbox(min(currentpoint[0], x1, x2, x3), min(currentpoint[1], y1, y2, y3), 
 	             max(currentpoint[0], x1, x2, x3), max(currentpoint[1], y1, y2, y3)))

    def write(self, canvas, file):
        file.write("%f %f %f %f %f %f curveto" % ( canvas.unit.pt(self.x1),
                                                   canvas.unit.pt(self.y1),
                                                   canvas.unit.pt(self.x2),
                                                   canvas.unit.pt(self.y2),
                                                   canvas.unit.pt(self.x3),
                                                   canvas.unit.pt(self.y3)) )
        
    def ConvertToBezier(self, currentpoint):
        return ((self.x3, self.y3), 
                bcurve(currentpoint[0], currentpoint[1],
                        self.x1, self.y1, self.x2, self.y2, self.x3, self.y3))


class rcurveto(pathel):
	
    def __init__(self, dx1, dy1, dx2, dy2, dx3, dy3):
        self.dx1 = dx1
	self.dy1 = dy1
	self.dx2 = dx2
	self.dy2 = dy2
	self.dx3 = dx3
	self.dy3 = dy3
	
    def write(self, canvas, file):
        file.write("%f %f %f %f %f %f rcurveto" % ( canvas.unit.pt(self.dx1),
                                                    canvas.unit.pt(self.dy1),
                                                    canvas.unit.pt(self.dx2),
                                                    canvas.unit.pt(self.dy2),
                                                    canvas.unit.pt(self.dx3),
                                                    canvas.unit.pt(self.dy3)) )

    def bbox(self, canvas, currentpoint, currentsubpath):
	x1=currentpoint[0]+canvas.unit.pt(self.dx1)
	y1=currentpoint[1]+canvas.unit.pt(self.dy1)
	x2=currentpoint[0]+canvas.unit.pt(self.dx2)
	y2=currentpoint[1]+canvas.unit.pt(self.dy2)
	x3=currentpoint[0]+canvas.unit.pt(self.dx3)
	y3=currentpoint[1]+canvas.unit.pt(self.dy3)
        return ((x3, y3),
                currentsubpath or currentpoint,
                bbox(min(currentpoint[0], x1, x2, x3), min(currentpoint[1], y1, y2, y3), 
 	             max(currentpoint[0], x1, x2, x3), max(currentpoint[1], y1, y2, y3)))
        
    def ConvertToBezier(self, currentpoint):
        x2=currenpoint(0)+self.dx1
        y2=currenpoint(1)+self.dy1
        x3=currenpoint(0)+self.dx2
        y3=currenpoint(1)+self.dy2
        x4=currenpoint(0)+self.dx3
        y4=currenpoint(1)+self.dy3
        return ((x4, y4), bcurve(x2, y2, x3, y3, x4, y4))

#
# path: PS style path 
#
	
class path:
    """ PS style path """
    def __init__(self, path=[]):
        self.path = path
        
    def __add__(self, other):
        return path(self.path+other.path)

    def __len__(self):
        return len(self.path)

    def __getitem__(self, i):
        return self.path[i]

    def bbox(self, canvas):
        currentpoint = None
        currentsubpath = None
        abbox = bbox()
        for pathel in self.path:
           (currentpoint, currentsubpath, nbbox) = pathel.bbox(canvas, currentpoint, currentsubpath)
           if abbox: abbox = abbox+nbbox
	return abbox
	
    def write(self, canvas, file):
	if not (isinstance(self.path[0], moveto) or
	        isinstance(self.path[0], arc) or
		isinstance(self.path[0], arcn)):
	    raise PathException, "first path element must be either moveto, arc, or arcn"
        for pathel in self.path:
	    pathel.write(canvas, file)
            file.write("\n")

    def append(self, pathel):
        self.path.append(pathel)

    def ConvertToBezier(self):
        currentpoint = None
        currentsubpath = None
        self.bpath = bpath()
        for pathel in self.path:
           (currentpoint, currentsubpath, bp) = pathel.ConvertToBezier(currentpoint, currentsubpath)
           if bp:
               for bpel in bp:
                  self.bpath.append(bpel)


class line(path):
   def __init__(self, x1, y1, x2, y2):
       path.__init__(self, [ moveto(x1,y1), lineto(x2, y2) ] )


class rect(path):
   def __init__(self, x, y, width, height):
       path.__init__(self, [ moveto(x,y), 
                             rlineto(width,0), 
			     rlineto(0,height), 
			     rlineto(-unit.length(width),0),
			     closepath()] )

#
# bpathel: element of Bezier path
#

class bpathel:
    def __init__(self, x0, y0, x1, y1, x2, y2, x3, y3):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.x3 = x3
        self.y3 = y3

    def __str__(self):
        return "%f %f moveto %f %f %f %f %f %f curveto" % (self.x0, self.y0,
                                                           self.x1, self.y1,
                                                           self.x2, self.y2,
                                                           self.x3, self.y3)

    def midpointsplit(self):
        ' splits bpathel at midpoint returning bpath with two bpathels '
        
        # first, we have to calculate the  midpoints between adjacent
        # control points
        x01 = 0.5*(self.x0+self.x1)
        y01 = 0.5*(self.y0+self.y1)
        x12 = 0.5*(self.x1+self.x2)
        y12 = 0.5*(self.y1+self.y2)
        x23 = 0.5*(self.x2+self.x3)
        y23 = 0.5*(self.y2+self.y3)

        # In the next iterative step, we need the midpoints between 01 and 12
        # and between 12 and 23 
        x01_12 = 0.5*(x01+x12)
        y01_12 = 0.5*(y01+y12)
        x12_23 = 0.5*(x12+x23)
        y12_23 = 0.5*(y12+y23)

        # Finally the midpoint is given by
        xmidpoint = 0.5*(x01_12+x12_23)
        ymidpoint = 0.5*(y01_12+y12_23)
        
        return bpath([bpathel(self.x0, self.y0, x01, y01,
                              x01_12, y01_12, xmidpoint, ymidpoint),
                      bpathel(xmidpoint, ymidpoint, x12_23, y12_23,
                              x23, y23, self.x3, self.y3)])
                       

#
# bpath: Bezier path
#

class bpath:
    """ path consisting of bezier curves"""
    def __init__(self, bpath=[]):
        self.bpath = bpath
	
    def append(self, bpathel):
        self.bpath.append(bpathel)

    def __add__(self, bp):
        return bpath(self.bpath+bp.bpath)

    def __len__(self):
        return len(self.bpath)

    def __getitem__(self, i):
        return self.bpath[i]

    def __str__(self):
        return reduce(lambda x,y: x+"%s\n" % str(y), self.bpath, "")

    def midpointsplit(self):
        result = []
        for bpel in self.bpath:
            sbp = bpel.midpointsplit()
            for sbpel in sbp:
                result.append(sbpel)
        return bpath(result)
       

class bcurve(bpath):
    """ bpath consisting of one bezier curve"""
    def __init__(self, x0, y0, x1, y1, x2, y2, x3, y3):
        bpath.__init__(self, [bpathel(x0, y0, x1, y1, x2, y2, x3, y3)]) 


class bline(bpath):
    """ bpath consisting of one straight line"""
    def __init__(self, x0, y0, x1, y1):
        bpath.__init__(self, 
                      [bpathel(x0, y0, 
                               x0+(x1-x0)/3.0, 
                               y0+(y1-y0)/3.0,
                               x0+2.0*(x1-x0)/3.0, 
                               y0+2.0*(y1-y0)/3.0,
                               x1, y1 )]) 


class barc(bpath):
    def __init__(self, x, y, r, phi1, phi2, dphimax=pi/4):

        phi1 = phi1*pi/180
        phi2 = phi2*pi/180

        if phi2<phi1:        
	    # guarantee that phi2>phi1 ...
	    phi2 = phi2 + (floor((phi1-phi2)/(2*pi))+1)*2*pi
        elif phi2>phi1+2*pi:
   	    # ... or remove unnecessary multiples of 2*pi
	    phi2 = phi2 - (floor((phi2-phi1)/(2*pi))-1)*2*pi
            
        if r==0 or phi1-phi2==0: return None

        subdivisions = abs(int((1.0*(phi1-phi2))/dphimax))+1

        dphi=(1.0*(phi2-phi1))/subdivisions

        self.bpath = []    

        for i in range(subdivisions):
            self.bpath.append(arctobpathel(x, y, r, phi1+i*dphi, phi1+(i+1)*dphi))


def arctobpathel(x, y, r, phi1, phi2):
    dphi=phi2-phi1

    if dphi==0: return None
    
    # the two endpoints should be clear 
    (x0, y0) = ( x+r*cos(phi1), y+r*sin(phi1) )
    (x3, y3) = ( x+r*cos(phi2), y+r*sin(phi2) )
   
    # optimal relative distance along tangent for second and third
    # control point
    l = r*4*(1-cos(dphi/2))/(3*sin(dphi/2))

    (x1, y1) = ( x0-l*sin(phi1), y0+l*cos(phi1) )
    (x2, y2) = ( x3+l*sin(phi2), y3-l*cos(phi2) )
    
    return bpathel(x0, y0, x1, y1, x2, y2, x3, y3)   


if __name__=="__main__":
    def testarc(x, y, phi1, phi2):
        print "1 0 0 setrgbcolor"
        print "newpath"
        print "%f %f 48 %f %f arc" % (x, y, phi1, phi2)
        print "stroke"
        print "0 1 0 setrgbcolor"
        print "newpath"
        print barc(x,y,50,phi1,phi2)
        print "stroke"

    def testarcn(x, y, phi1, phi2):
        print "1 0 0 setrgbcolor"
        print "newpath"
        print "%f %f 48 %f %f arcn" % (x, y, phi1, phi2)
        print "stroke"
        print "0 1 0 setrgbcolor"
        print "newpath"
        print barc(x,y,50,phi2,phi1)
        print "stroke"
       
    print "%!PS-Adobe-2.0"
    #print "newpath" 
    #print arctobpath(100,100,100,0,90,dphimax=90)
    #print arctobpath(100,100,100,0,90)
    #print "stroke"

    testarc(100, 200, 0, 90)
    testarc(200, 200, -90, 90)
    testarc(300, 200, 270, 90)
    testarc(400, 200, 90, -90)
    testarc(500, 200, 90, 270)
    testarc(400, 300, 45, -90)
    testarc(200, 300, 45, -90-2*360)
    testarc(100, 300, 45, +90+2*360)

    testarcn(100, 500, 0, 90) 
    testarcn(200, 500, -90, 90) 
    testarcn(300, 500, 270, 90) 
    testarcn(400, 500, 90, -90) 
    testarcn(500, 500, 90, 270) 
    testarcn(400, 600, 45, -90) 
    testarcn(200, 600, 45, -90-360) 
    testarcn(100, 600, 45, -90+360) 

    p=path([moveto(100,100), rlineto(20,20), arc(150,120,10,30,300),closepath()])
    p.ConvertToBezier()
    print p.bpath
    bpsplit=p.bpath.midpointsplit()
    print "stroke"
    print "1 0 0 setrgbcolor"
    print "newpath"
    print bpsplit
    print "stroke"
#    p=path([arc(120,120,10,30,360)])
#    p.ConvertToBezier()
#    print p.bpath
#    print "stroke"
    print "showpage"
