 # -*- coding: utf-8 -*-
import bpy
import numpy as np

bl_info = {
    'name': 'Springs generator',
    'author': 'Elbio Peña <elbioemilio@outlook.es>',
    'version': (6, 0),
    'blender': (2, 83, 0),
    'category': 'Mesh',
    'location': 'Operator Search',
    'description': 'Generates 3 types of springs',
    'warning': 'Experimental',
    'doc_url': '',
    'tracker_url': ''}


class MESH_OT_springs(bpy.types.Operator):
    """"Generates tension spring and compresion spring meshes"""
    bl_idname = "mesh.add_springs"
    bl_label = "Add Springs"
    bl_options = {'REGISTER', 'UNDO'}

    D: bpy.props.FloatProperty(
        name = "Spring Diam",
        description = "Outside Diameter",
        default=15)
    d: bpy.props.FloatProperty(
        name = "Wire Diam",
        description = "Wire Diameter",
        default=2)
    D2: bpy.props.FloatProperty(
        name="Hook Diam",
        description="Hook Inside Diameter",
        default=15)
    H: bpy.props.FloatProperty(
        name="Height",
        description="Height of spiral",
        default=35, min=0.001, max=350)
    p: bpy.props.FloatProperty(
        name="Pitch",
        description="Turns/units of height",
        default=0.0008, min=0, max=40000)
    h: bpy.props.FloatProperty(
        name="Neck",
        description="Height of the hook neck",
        default=0.0, min=0)
    mat: bpy.props.IntProperty(
        name = "material",
        description = "1-Chomium\n2-Black oxide\n3-Stainless steel\n4-Zinc",
        default=0, min=0, max=3)
    hook_type : bpy.props.IntProperty(
        name = "Hook type",
        description = "1= open hook, 2= Closed hook, 3= None",
        default=1, min=0, max=3)
    hook_angle : bpy.props.IntProperty(
        name = "Hook angle",
        description = "1 = 180, 2 = 90",
        default=1, min=1, max=2)
    __spring_bones: bpy.props.IntProperty(
        name = "Bones",
        description = "Number of spiran bonbes",
        default=0)

    def execute(self, context):
        """This creates the spring in the following steps:
        ===============================================
        A)Draw the mesh
        ---------------
        I ) First calculate the points of the central line inside the coil of
            the spring, in 5 parts (the order is different in the code):
                1-lower hook
                2-lower segment conecting hook and coil
                3-coil
                4-upper segment conecting hook and coil
                5-upper hook
        II) Draw spring central line with the coordinates of the points by
            creating a point and extruding the point trhough each coordinates.
        III)Convert to spline and from spline to mesh with offset = coil diam.

        B)Draw caps at both open ends
        -----------------------------
        C) Draw central & control armatures
        -----------------------------------
        D)Add constraints to the armatures
        ----------------------------------"""
        # ########### INITIAL SETTINGS ##############

        # trasform to millimeters
        self.D = self.D/1000
        self.d = self.d/1000
        self.D2 = self.D2/1000
        self.H = self.H/1000
        self.h = self.h/1000

        # Save current settings
        scene = bpy.data.scenes["Scene"]
        pivot_point = scene.tool_settings.transform_pivot_point
        orientation = scene.transform_orientation_slots[0].type
        auto_merge = scene.tool_settings.use_mesh_automerge
        unit_system = scene.unit_settings.system
        scale_length = scene.unit_settings.scale_length
        unit_length = scene.unit_settings.length_unit
        cursor_loc = list(scene.cursor.location)

        scene.tool_settings.transform_pivot_point = 'ACTIVE_ELEMENT'
        scene.tool_settings.use_mesh_automerge = False
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        scene.unit_settings.length_unit = 'MILLIMETERS'
        scene.cursor.location = (0, 0, 0)
        scene.transform_orientation_slots[0].type = 'GLOBAL'

        # ########### VARIABLE CONSTRAITNS ##############

        # Adjust pitch for integer number of turns
        print(self.H, self.d)
        kn = (self.H - 0.1*self.d)/(1.1*self.d)//1
        self.p = kn/self.H

        # decrease wire diam if outside diam or hook diam gets too small
        if 3*self.d > self.D:
            self.d = self.D/2
        if 2*self.d > self.D2:
            self.d = self.D2/2
        # stop increasing hook diam if it gets too big
        if self.D2 > 1.5*self.D:
            self.D2 = 1.5*self.D
        # stop decreasing hook diam if it gets too small
        if self.D2 < self.D/1.5:
            self.D2 = self.D/1.5

        n = 10     # number of hooks longitudinal steps
        N = 15*self.p*self.H//1  # nomber of spiral longitudinal steps/turn
        k = 3      # radial resolution

        # ########### CALCULATE POINTS FOR CENTRAL LINE ##############

        def remove_doubles(x, y, z):
            """unique values for dots with euclidean distance less than
            0.00001 which are esentially the same point"""
            size = len(x)
            xi = x[1:]-x[0:size-1]
            yi = y[1:]-y[0:size-1]
            zi = z[1:]-z[0:size-1]
            dist = np.sqrt(np.power(xi, 2) + np.power(yi, 2) + np.power(zi, 2))
            index = np.where(dist <= 0.00001)
            x = np.delete(x, index)
            y = np.delete(y, index)
            z = np.delete(z, index)
            print(f"Removed {size-len(x)} vertices...")
            return x, y, z

        if self.hook_angle == 2:
            self.p = self.p + 0.25/self.H

        #  coil coordinates
        u = np.linspace(self.H, 0, N)

        if self.hook_type == 3:
            z1 = np.linspace(self.H-0.3*self.d/2,  0+0.3*self.d/2,  N)
        else:
            z1 = u
        x1 = (self.D/2)*np.cos(2*np.pi*self.p*u)
        y1 = (self.D/2)*np.sin(2*np.pi*self.p*u)

        def find_angle(x, y):
            angle = round(np.arctan(y/x), 2)
            if x < 0 and y > 0:
                angle += np.pi
            elif x < 0 and y < 0:
                angle += np.pi
            elif x > 0 and y < -0.00001:
                angle += 2*np.pi
            return angle
        alpha = find_angle(x1[0], y1[0])

        # angles for the "s" segments
        if self.hook_type == 1 or self.hook_type == 2:
            li = 7              # length ratio li:1
            sleng = np.zeros(n + 1)   # segments lengths
            rate = (li-1)/(n-1)
            for i in range(n):
                sleng[i] = 6 - i*rate
            sleng = 1/2*np.pi*sleng/np.sum(sleng)

            u = np.hstack([[2*np.pi],  np.zeros(n)])
            for i in range(n):
                u[i+1] = 2*np.pi - np.sum(sleng[0:i+1])
        elif self.hook_type == 3:
            last = (4*np.pi/5)*(0.5)/(self.d*self.p)
            if last > 4/3*np.pi:
                last = 4/3*np.pi
            u = np.linspace(0, last, n)

        # Lower s segment
        if self.hook_type == 1:
            x2 = self.D/2*abs(np.cos(u))
            XG2 = self.D2/2*abs(np.cos(u))
            y2 = self.D2/2*np.sin(u)
            z2 = np.sqrt(abs((self.D2/2)**2-np.power(XG2,  2)))-self.D2/2
            z2 = z2[-1::-1]
        elif self.hook_type == 2:
            x2 = (self.D/2-1.025*self.d)*abs(np.cos(u))+1.025*self.d
            XG2 = self.D2/2*abs(np.cos(u))
            y2 = self.D2/2*np.sin(u)
            z2 = np.sqrt(abs((self.D2/2)**2-np.power(XG2,  2)))-self.D2/2
            z2 = z2[-1::-1]
        elif self.hook_type == 3:
            x2 = self.D/2*np.cos(u)
            y2 = -self.D/2*np.sin(u)
            z2 = np.zeros(len(u))+0.3*self.d/2

        # Upper s segment
        if self.hook_type == 1:
            u1 = u[-1::-1]
            if self.hook_angle == 1:
                x4 = self.D/2*(np.cos(u1+alpha))
                XG4 = self.D2/2*(abs(np.cos(u1)))
                y4 = self.D2/2*(-np.sin(u1+alpha))
            elif self.hook_angle == 2:
                x4 = self.D2/2*(-np.cos(u1+alpha))
                XG4 = self.D2/2*(abs(np.cos(u1)))
                y4 = (self.D/2)*(np.sin(u1+alpha))
            z4 = -np.sqrt(abs((self.D2/2)**2-np.power(XG4, 2)))
            z4 = (z4 + self.D2/2 + self.H)[-1::-1]

        elif self.hook_type == 2:
            u1 = u[-1::-1]
            if self.hook_angle == 1:
                x4 = (self.D/2-1.01*self.d)*abs(np.cos(u1))+1.01*self.d
                XG4 = self.D2/2*(abs(np.cos(u1)))
                y4 = self.D2/2*(- np.sin(u1))
            elif self.hook_angle == 2:
                x4 = -(self.D2/2)*np.cos(u1 + alpha)
                XG4 = self.D2/2*(abs(np.cos(u1)))
                y4 = (self.D/2-1.01*self.d)*(np.sin(u1 + alpha))+1.01*self.d
            z4 = -np.sqrt(abs((self.D2/2)**2-np.power(XG4, 2)))
            z4 = (z4 + self.D2/2 + self.H)[-1::-1]
        elif self.hook_type == 3:
            u1 = u + alpha
            x4 = self.D/2*np.cos(u1[-1::-1])
            y4 = self.D/2*np.sin(u1[-1::-1])
            z4 = np.full(len(u), self.H)-0.3*self.d/2

        # lower circular segment
        if self.hook_type == 1:
            u1 = np.linspace(np.pi, 2*np.pi, n)
            y3 = self.D2/2*np.cos(u1)
            z3 = self.D2/2*np.sin(u1)-self.D2/2-self.h-self.d
            x3 = self.D/2*np.zeros(len(u1))

        elif self.hook_type == 2:
            u1 = np.linspace(4*np.pi, 0, 4*n)
            x3 = ((u1-2*np.pi)/(4*np.pi)*2.05*self.d)
            y3 = -self.D2/2*np.cos(u1)
            z3 = self.D2/2*(-np.sin(u1)-1)[-1::-1]
        elif self.hook_type == 3:
            x3, y3, z3 = ([], [], [])

        # Upper circular segment
        if self.hook_type == 1:
            u1 = np.linspace(np.pi, 0, n)
            if self.hook_angle == 1:
                y5 = self.D2/2*np.cos(u1)
                x5 = np.zeros(len(u1))
            elif self.hook_angle == 2:
                x5 = self.D2/2*np.cos(u1[-1::-1])
                y5 = np.zeros(len(u1[-1::-1]))

            z5 = (self.D2/2*np.sin(u1)+self.D2/2+self.H+self.h+self.d)
        elif self.hook_type == 2:
            u1 = np.linspace(4*np.pi, 0, 4*n)
            if self.hook_angle == 1:
                x5 = ((-u1+2*np.pi)/(4*np.pi)*2*self.d)  # -.0625*self.d
                y5 = self.D2/2*np.cos(u1)
            if self.hook_angle == 2:
                y5 = ((-u1+2*np.pi)/(4*np.pi)*2*self.d)  # +.5*self.d)
                x5 = -self.D2/2*np.cos(u1)  # [-1::-1]
            z5 = self.D2/2*np.sin(u1)+self.D2/2+self.H
        elif self.hook_type == 3:
            x5, y5, z5 = ([], [], [])

        # Unifying all coordinates into a single entity
        x = np.hstack([x5[:-1], x4, x1, x2, x3])
        y = np.hstack([y5[:-1], y4, y1, y2, y3])
        z = np.hstack([z5[:-1], z4, z1, z2, z3])

        # length of the spring
        last = len(x)-1
        xa = np.power(x[1:]-x[0:last], 2)
        ya = np.power(y[1:]-y[0:last], 2)
        za = np.power(z[1:]-z[0:last], 2)
        L = np.sum(np.sqrt(xa+ya+za))

        self.D = self.D+self.d
        self.D2 = self.D2-self.d

        # Create name based upon the dimensions
        # wire thickness x coil_outside_diam x hook_inside_diam x
        # distance_between_hook_centers
        name = ""
        if (self.d*1000) % 1 > 0.1:
            name += str(round(self.d*1000, 2))
        else:
            name += str(int(self.d*1000))

        if (self.D*1000) % 1 > 0.1:
            name += " x " + str(round(self.D*1000, 1))
        else:
            name += " x " + str(int(self.D*1000))

        if self.hook_type == 1 or self.hook_type == 2:
            if round(self.D2*1000, 3) % 1 > 0.01:
                name += " x " + str(round(self.D2*1000, 1))
                print(self.D2*1000)
            else:
                name += " x " + str(int(round(self.D2*1000, 3)))

        name_l = round(self.H*1000+self.D2*1000+self.h*1000*2+3*self.d*1000, 3)
        if name_l % 1 > 0.01:
            print(name_l)
            name += " x " + str(round(name_l, 1))
        else:
            name += " x " + str(int(name_l))

        self.D = self.D-self.d
        self.D2 = self.D2+self.d

        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        layer = context.view_layer.layer_collection.children[collection.name]
        bpy.context.view_layer.active_layer_collection = layer

        # Draw the spring central line
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        scene.cursor.location = (x[0], y[0], z[0])
        bpy.ops.mesh.primitive_vert_add()
        x, y, z = remove_doubles(x, y, z)
        size = len(x) - 1

        for i in range(size):
            bpy.ops.mesh.extrude_vertices_move(
                MESH_OT_extrude_verts_indiv={"mirror": False},
                TRANSFORM_OT_translate={"value": (x[i+1]-x[i], y[i+1]-y[i],
                                                  z[i+1]-z[i]),
                                        "orient_type": 'LOCAL'})

        # Create a mesh from spline bevel
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.convert(target='CURVE')
        spring = context.active_object
        spring.name = 'Spring mesh'
        geometry = spring.data.splines.id_data.name
        bpy.data.curves[geometry].bevel_depth = self.d/2
        bpy.data.curves[geometry].bevel_resolution = k
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.shade_smooth()

        # #Add slots assign the material to the mesh
        # materials = ["Chromium","Black oxide","Stainless steel","Zinc"]
        # for i,mat in enumerate(materials):
        #     bpy.ops.object.material_slot_add()
        #     spring.data.materials[i] = bpy.data.materials[mat]
        # spring.active_material_index = self.mat
        # bpy.ops.object.mode_set(mode = "EDIT")
        # bpy.ops.mesh.select_all(action="SELECT")
        # bpy.ops.object.material_slot_assign()
        # bpy.ops.mesh.select_all(action="DESELECT")
        # bpy.ops.object.mode_set(mode = "OBJECT")

        # Add edge loops for beter shading and close cap and tail.
        context.tool_settings.mesh_select_mode = (True, False, False)
        for i in np.arange(0, 10, 1):
            spring.data.vertices[i].select = True
        bpy.ops.object.mode_set(mode="EDIT")

        if self.hook_type == 1:
            bpy.ops.transform.resize(value=(1, 1, 0))
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                                "value": (0, 0, -0.2*self.D2)})
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                                "value": (0, 0, -0.1*self.d)})
        elif self.hook_type == 2:
            bpy.ops.transform.resize(value=(1, 1, 0))
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                                "value": (0, 0, 0.1*self.d)})
        elif self.hook_type == 3:
            v0 = context.active_object.data.polygons[0].normal
            v1 = context.active_object.data.polygons[1].normal
            normal = np.cross(v0, v1)
            normal = normal/np.sqrt(np.sum(np.power(normal, 2)))
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                     "value": tuple(-0.1*L/(N+4*n+1)*normal)})
        bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                                    "value": (0, 0, 0)})
        bpy.ops.transform.resize(value=(0.7, 0.7, 0.7), orient_type="LOCAL")
        bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                                        "value": (0, 0, 0)})
        bpy.ops.mesh.merge(type='CENTER')

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode="OBJECT")
        size = len(list(spring.data.vertices))

        if self.hook_type == 1:
            for i in np.arange(size-41, size-31, 1):
                spring.data.vertices[i].select = True
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.transform.resize(value=(1, 1, 0))
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                        "value": (0, 0, 0.2*self.D2), "orient_type": "LOCAL"})
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                            "value": (0, 0, 0.1*self.d)})
        elif self.hook_type == 2:
            for i in np.arange(size-31, size-21, 1):
                spring.data.vertices[i].select = True
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.transform.resize(value=(1, 1, 0))
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                                "value": (0, 0, -0.1*self.d)})
        elif self.hook_type == 3:
            for i in np.arange(size-31, size-21, 1):
                spring.data.vertices[i].select = True
            bpy.ops.object.mode_set(mode="EDIT")
            v0 = context.active_object.data.polygons[-31].normal
            v1 = context.active_object.data.polygons[-32].normal
            normal = np.cross(v0, v1)
            normal = normal/np.sqrt(np.sum(np.power(normal, 2)))
            bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                "value": tuple(-0.15*L/(N+4*n+1)*normal)})
        bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                                    "value": (0, 0, 0)})
        bpy.ops.transform.resize(value=(0.7, 0.7, 0.7), orient_type="LOCAL")
        bpy.ops.mesh.extrude_edges_move(TRANSFORM_OT_translate={
                                "value": (0, 0, 0), "orient_type": 'GLOBAL'})
        bpy.ops.mesh.merge(type='CENTER')
        bpy.ops.object.mode_set(mode="OBJECT")
        spring.data.vertices[-1].select = False

        if self.hook_type == 3:
            bpy.ops.mesh.primitive_cube_add(size=(
                                self.D+self.d)*1.1,
                                enter_editmode=True, align='WORLD',
                                location=(0, 0, -(1.1*(self.D+self.d)/2)))
            bpy.ops.mesh.primitive_cube_add(
                            size=(self.D+self.d)*1.1,
                            enter_editmode=False, align='WORLD',
                            location=(0, 0, (self.H+1.1*(self.D+self.d)/2)))
            bpy.ops.object.mode_set(mode="OBJECT")
            sustract = context.active_object
            sustract.select_set(False)
            context.view_layer.objects.active = spring
            spring.select_set(True)
            bpy.ops.object.modifier_add(type='BOOLEAN')
            modifier = bpy.data.objects[spring.name].modifiers["Boolean"]
            modifier.operation = 'DIFFERENCE'
            modifier.object = sustract
            bpy.ops.object.modifier_apply(apply_as='DATA',  modifier='Boolean')
            bpy.data.objects[spring.name].select_set(False)
            bpy.data.objects[sustract.name].select_set(True)
            bpy.ops.object.delete(use_global=False)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.00001)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
        bpy.ops.object.transform_apply(location=True,
                                       rotation=True, scale=True)

        # Create central spring armature

        u = np.linspace(self.H, 0, N/3)
        if self.hook_type == 3:
            z1 = np.linspace(self.H-0.3*self.d/2,  0+0.3*self.d/2,  N/3)
        else:
            z1 = u
        x1 = (self.D/2+self.d)*np.cos(2*np.pi*self.p*u)
        y1 = (self.D/2+self.d)*np.sin(2*np.pi*self.p*u)

        x_up_hook = np.hstack([x5[::3],  x4[::3]])
        y_up_hook = np.hstack([y5[::3],  y4[::3]])
        z_up_hook = np.hstack([z5[::3],  z4[::3]])
        up_len = len(x_up_hook)

        x_lo_hook = np.hstack([x2[::3],  x3[::3]])
        y_lo_hook = np.hstack([y2[::3],  y3[::3]])
        z_lo_hook = np.hstack([z2[::3],  z3[::3]])
        lo_len = len(x_lo_hook)

        x = np.hstack([x_up_hook, x1, x_lo_hook])
        y = np.hstack([y_up_hook, y1, y_lo_hook])
        z = np.hstack([z_up_hook, z1, z_lo_hook])
        x, y, z = remove_doubles(x, y, z)

        scene.cursor.location = (x[0], y[0], z[0])
        bpy.ops.object.armature_add()
        bpy.ops.object.mode_set(mode='EDIT')
        scene.cursor.location = (x[1], y[1], z[1])
        bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)

        size = len(x)
        for i in range(size-2):
            bpy.ops.armature.extrude_move(
                ARMATURE_OT_extrude={"forked": False},
                TRANSFORM_OT_translate={
                    "value": (x[i+2]-x[i+1],
                              y[i+2]-y[i+1], z[i+2]-z[i+1]),
                    "orient_type": 'GLOBAL'})

        bpy.ops.armature.select_all(action='SELECT')
        bpy.ops.view3d.snap_cursor_to_selected()

        spring_armature = context.active_object
        spring_armature.name = "Spring armature"
        roll = bpy.data.objects[spring_armature.name].data.edit_bones[
                                                        size-lo_len-1].roll
        for i in [up_len-1, size-lo_len-1]:
            bpy.data.objects[
                spring_armature.name].data.edit_bones[i].select = False
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        self.__spring_bones = size-1
        bpy.ops.object.transform_apply(location=True,
                                       rotation=True, scale=True)

        # Mark the two middle bones with digital signature just for fun :-)
        spring_armature.data.bones[8].name = 'Elbio Peña'
        if size-2 >= 17:
            position = 17
        else:
            position = 7
        spring_armature.pose.bones[position].name = "Elbio Peña"

        # add empties
        bpy.ops.object.mode_set(mode="OBJECT")

        if self.hook_type == 1:
            up_location = (0, 0, self.H + self.D2/2 + self.h + self.d)
            lo_location = (0, 0, -self.D2/2-self.h-self.d)
        elif self.hook_type == 2:
            up_location = (0, 0, self.H + self.D2/2)
            lo_location = (0, 0, -self.D2/2)
        elif self.hook_type == 3:
            up_location = (0, 0, self.H)
            lo_location = (0, 0, 0)

        scene.cursor.location = up_location
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        up_driver = context.active_object
        up_driver.empty_display_size = 0.55*self.D
        up_driver.name = "Upper driver"

        scene.cursor.location = lo_location
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        lo_driver = context.active_object
        lo_driver.empty_display_size = 0.55*self.D
        lo_driver.name = "Lower driver"

        # Add control armatures and parent to empties
        scene.cursor.location = up_location
        bpy.ops.object.armature_add(radius=self.D/25)
        up_armature = context.active_object
        up_armature.name = "Upper armature"
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.transform.rotate(value=np.pi, orient_axis='Y')
        coord_1 = np.array([x[up_len-1],  y[up_len-1],  z[up_len-1]])
        coord_2 = np.array([x[up_len-2],  y[up_len-2],  z[up_len-2]])
        vec = coord_1 - coord_2
        coord_3 = coord_2 + vec/100
        scene.cursor.location = coord_2
        bpy.ops.armature.bone_primitive_add()
        scene.cursor.location = coord_3
        bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        up_anchor = up_armature.data.bones[1]
        up_anchor.name = 'Upper anchor'
        up_guide = up_armature.data.bones[0]
        up_guide.name = 'Upper guide'
        up_anchor.select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.armature.parent_set(type='OFFSET')
        bpy.ops.object.mode_set(mode="OBJECT")
        context.view_layer.objects.active = up_driver
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

        scene.cursor.location = lo_location
        bpy.ops.object.armature_add(radius=self.D/25)
        bpy.ops.object.mode_set(mode="OBJECT")
        lo_armature = context.active_object
        lo_armature.name = "Lower armature"
        bpy.ops.object.mode_set(mode="EDIT")
        coord_1 = np.array([x[size-lo_len-1], y[size-lo_len-1],
                            z[size-lo_len-1]])
        coord_2 = np.array([x[size-lo_len], y[size-lo_len],
                            z[size-lo_len]])
        vec = coord_2 - coord_1
        coord_3 = coord_2 + vec/100
        scene.cursor.location = coord_2
        bpy.ops.armature.bone_primitive_add()
        scene.cursor.location = coord_3
        bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        lo_anchor = lo_armature.data.bones[1]
        lo_anchor.name = 'Lower anchor'
        lo_guide = lo_armature.data.bones[0]
        lo_guide.name = 'Lower guide'
        lo_anchor.select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.armature.parent_set(type='OFFSET')
        bpy.ops.object.mode_set(mode="OBJECT")
        context.view_layer.objects.active = lo_driver
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
        context.view_layer.objects.active = lo_armature
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.data.objects[lo_armature.name].data.edit_bones[1].roll = roll
        bpy.ops.object.mode_set(mode="OBJECT")

        # Add damped track constraints upper and lower guides
        context.view_layer.objects.active = up_armature
        up_armature.data.bones.active = up_armature.data.bones[0]
        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.pose.constraint_add(type='DAMPED_TRACK')
        bone_constraint = up_armature.pose.bones[0].constraints['Damped Track']
        bone_constraint.target = lo_driver
        bone_constraint.track_axis = 'TRACK_Y'
        bone_constraint.influence = 1.0
        bpy.ops.object.mode_set(mode="OBJECT")

        context.view_layer.objects.active = lo_armature
        lo_armature.data.bones.active = lo_armature.data.bones[0]
        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.pose.constraint_add(type='DAMPED_TRACK')

        bone_constraint = lo_armature.pose.bones[0].constraints['Damped Track']
        bone_constraint.target = up_driver
        bone_constraint.track_axis = 'TRACK_Y'
        bone_constraint.influence = 1.0
        bpy.ops.object.mode_set(mode="OBJECT")
        lo_armature.select_set(False)

        # add iverse kinematics to spring armature last bone
        context.view_layer.objects.active = spring_armature
        ik_bone = spring_armature.data.bones[size-lo_len-1]
        spring_armature.data.bones.active = ik_bone
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        bpy.ops.pose.constraint_add(type="IK")
        bpy.ops.object.mode_set(mode="OBJECT")
        ik_bone = spring_armature.pose.bones[size-lo_len-1]
        ik_bone.constraints["IK"].target = lo_armature
        lo_anchor = lo_armature.data.bones[1]
        ik_bone.constraints["IK"].subtarget = lo_anchor.name
        ik_bone.constraints["IK"].chain_count = size-lo_len-up_len
        ik_bone.constraints["IK"].use_tail = True
        ik_bone.constraints["IK"].use_stretch = True
        ik_bone.constraints["IK"].use_location = True
        ik_bone.constraints["IK"].use_rotation = True
        ik_bone.constraints["IK"].weight = 1.0
        ik_bone.constraints["IK"].orient_weight = 1.0
        ik_bone.constraints["IK"].influence = 1.0

        # parent spring armature first bone to upper anchor
        bpy.data.objects[lo_armature.name].select_set(False)
        bpy.data.objects[spring_armature.name].select_set(True)
        spring_armature.pose.bones[up_len].bone.select = True
        up_armature.data.bones.active = up_armature.pose.bones[1].bone
        up_armature.data.bones[0].select = False
        up_armature.data.bones[1].select = True
        context.view_layer.objects.active = up_armature
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.object.parent_set(type='BONE')
        bpy.ops.object.mode_set(mode='OBJECT')

        #  parent spring mesh to spring armature and set final settings
        bpy.data.objects[spring.name].select_set(True)
        context.view_layer.objects.active = spring_armature
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')

        context.view_layer.objects.active = lo_driver
        bpy.ops.object.constraint_add(type='COPY_ROTATION')
        lo_driver.constraints['Copy Rotation'].target = up_driver
        bpy.data.objects[spring.name].hide_select = False
        spring_armature.hide_render = True
        up_armature.hide_render = True
        lo_armature.hide_render = True
        spring_armature.display_type = "BOUNDS"
        context.view_layer.objects.active = spring

        up_driver.select_set(True)
        up_armature.select_set(True)
        lo_driver.select_set(True)
        lo_armature.select_set(True)

        # move everything to the original curso location
        context.view_layer.objects.active = lo_driver
        scene.tool_settings.transform_pivot_point = 'ACTIVE_ELEMENT'
        scene.cursor.location = lo_location
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        bpy.ops.transform.translate(value=cursor_loc, orient_type='GLOBAL')
        scene.cursor.location = cursor_loc

        # Restore original settings
        if self.hook_angle == 2:
            self.p = self.p - 0.25/self.H
        scale_length = scene.unit_settings.scale_length
        unit_length = scene.unit_settings.length_unit
        cursor_loc = list(scene.cursor.location)

        self.D = self.D*1000
        self.d = self.d*1000
        self.D2 = self.D2*1000
        self.H = self.H*1000
        self.h = self.h*1000

        scene.tool_settings.transform_pivot_point = pivot_point
        scene.transform_orientation_slots[0].type = orientation
        scene.tool_settings.use_mesh_automerge = auto_merge
        scene.unit_settings.system = unit_system
        scene.unit_settings.scale_length = scale_length
        scene.unit_settings.length_unit = unit_length
        scene.cursor.location = cursor_loc

        return {'FINISHED'}


class VIEW3D_PT_springs_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Springs"
    bl_label = "Properties"

    def draw(self, context):
        self.layout.operator('mesh.add_springs')


def register():
    bpy.utils.register_class(MESH_OT_springs)
    bpy.utils.register_class(VIEW3D_PT_springs_panel)
    print("oh yeah")


def unregister():
    bpy.utils.unregister_class(MESH_OT_springs)
    bpy.utils.unregister_class(VIEW3D_PT_springs_panel)
