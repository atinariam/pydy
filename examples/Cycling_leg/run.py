#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 28 19:36:25 2017

@author: Anita Le Mair
"""
import numpy as np
from scipy.integrate import odeint
from sympy import sin, solve, symbols
from sympy import Derivative, Matrix
from sympy.physics.mechanics import (find_dynamicsymbols, dynamicsymbols,
                                     inertia)
from sympy.physics.mechanics import (Point, ReferenceFrame,
                                     RigidBody, KanesMethod)
from pydy.codegen.ode_function_generators import generate_ode_function

# Symbols for generalised coordinates and generatised speeds
q1, q2 = dynamicsymbols('q1 q2')
u1, u2 = dynamicsymbols('u1 u2')

# Symbols for the angle and angular velocity of the pedal
theta, omega = dynamicsymbols('theta omega')

# Diameter, mass and gravitational acceleration
r, m, g = symbols('r m g')

# various lengths and distances. See figure
bb, ob, ta, d1, d2 = symbols('bb ob ta d1 d2')

t = dynamicsymbols._t

# Reference Frames
N = ReferenceFrame('N')
A = N.orientnew('A', 'Axis', [q1, N.z])
B = A.orientnew('B', 'axis', [q2, A.z])
C = N.orientnew('C', 'Axis', [theta, N.z])

# Joints location and speed
J0 = Point('J0')
J0.set_vel(N, 0)
J1 = J0.locatenew('J1', bb*A.y)
J2 = J1.locatenew('J2', ob*B.y)
J1.v2pt_theory(J0, N, A)
J2.v2pt_theory(J1, N, B)

#Pedal position and speed
O = Point('O')
O.set_pos(J0, -d2*N.x + d1*N.y)
O.set_vel(N, 0*N.z)
S = O.locatenew('S', -ta*C.y) # hoek van pedaal vanaf het hoogste punt van de cirkel
S.v2pt_theory(O, N, C)

# Centres of mass and speed
P = J0.locatenew('P', 0.5*bb*A.y)
R = J1.locatenew('R', 0.5*ob*B.y)
T = O.locatenew('T', 0.5*ta*C.y)
P.v2pt_theory(J0, N, A)
R.v2pt_theory(J1, N, B)
T.v2pt_theory(O, N, C)

# Bodies 
IP = inertia(A, 1/12*m*(3*r**2+bb**2), 0, 1/12*m*(3*r**2+bb**2))
IP_tuple = (IP, P)
IR = inertia(B, 1/12*m*(3*r**2+ob**2), 0, 1/12*m*(3*r**2+ob**2))
IR_tuple = (IR, R)
IBody = inertia(C, 1/12*0.1*m*(ta)**2, 0, 1/12*0.1*m*(ta)**2)
IBody_tuple = (IBody, T)
BodyP = RigidBody('BodyP', P, A, m, IP_tuple)
BodyR = RigidBody('BodyR', R, B, m, IR_tuple)
Pedaal = RigidBody('Pedaal', T, C, 0.1*m, IBody_tuple)

#Force list and body list
FL = [(P, m * g * N.y), 
      (R, m * g * N.y), 
      (A,(-75*q1-0.01*u1)*A.z),
      (B,(-25*q2*B.z)),
      (C,(-25*C.z))]
BL = [BodyP, BodyR, Pedaal]

# Define configuration constraints and obtain velocity constraints
cc = [J2.pos_from(S).magnitude()]
kd = [q1.diff() - u1, q1.diff() + q2.diff() - u2, theta.diff() - omega]
kd_map = solve(kd, [qi.diff() for qi in [q1, q2, theta]])
vc = [x.subs(kd_map) for x in [cc[0].diff(dynamicsymbols._t)]]
    
constants = [m, g, r, ob, bb, ta, d1, d2]
coordinates = [q1, theta]
speeds = [u1, omega]
KM = KanesMethod(
    N,
    q_ind=coordinates,
    u_ind=speeds,
    kd_eqs=kd,
    q_dependent=[q2],
    configuration_constraints=cc,
    u_dependent=[u2],
    velocity_constraints=vc)
(fr, frstar) = KM.kanes_equations(FL, BL)

# looks like some of the derivative terms were not substituted correctly
forcing_vector = KM.forcing.subs(kd_map)
derivative_generator = (expr.atoms(Derivative)
                        for expr in find_dynamicsymbols(forcing_vector))
if frozenset().union(*(derivative_generator)):
    forcing_vector = forcing_vector.subs(kd_map)

#List apprehension
kdd = KM.kindiffdict()
coord_derivs = Matrix([kdd[c.diff()] for c in KM.q])

#RHS = mass_matrix.LU_solve(forcing_vector)
RHS = generate_ode_function(forcing_vector, KM.q, KM.u, constants,
                            mass_matrix=KM.mass_matrix,
                            coordinate_derivatives=coord_derivs,
                            constants_arg_type='dictionary')

# Initial conditions, time and constant values
# q = [q1,theta,q2,q1dot,omega,q2dot]
q0 = np.deg2rad((45, 0, 60, 0, 0.5, 0))
constants = {m: 7.5, g: 10, r:0.2, bb: 0.5, ob: 0.4, ta:0.18, d1: 0.62, d2:0.18}
t = np.linspace(0,5,10000)

# Simulation en results
result = odeint(RHS, q0, t, args=(constants,))
q = np.rad2deg(result)

plt.figure(1)
plt.grid(True)
plt.plot(t,q[:,0],'-', linewidth = 2, label = 'q1')
plt.plot(t,q[:,2], '--', linewidth = 2, label = 'q2')
plt.legend()
plt.title('Angles upper leg q1 and lower leg q2')
plt.xlabel('Time (sec)')
plt.ylabel('Angle (deg)')
plt.figure(2)
plt.title('Position of the pedal')
plt.xlabel('Time (sec)')
plt.plot(0.18*np.sin(q[:,1]), 0.18*np.cos(q[:,1]))
plt.show()
