#%%
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import numpy as np

def volume(front_vertices,rear_vertices,colors = [0,0,1,1]):
    #[(+,+,-),(+,-,-),(-,-,-),(-,+,-),(+,+,+)(+,-,+)(-,-,+)(-,+,+)]
    vc_f = (front_vertices.max(axis = 0)+front_vertices.min(axis = 0))/2
    vc_r = (rear_vertices.max(axis = 0)+rear_vertices.min(axis = 0))/2
    front_vertices = np.vstack((vc_f,front_vertices), dtype=np.float32)
    rear_vertices = np.vstack((vc_r,rear_vertices), dtype=np.float32)
    index = np.arange(1,len(front_vertices))
        
    edges_f = np.array([[i,i+1] for i in index[:-1]]+[[index[-1],1]], dtype=np.uint32)
    edges_r = len(front_vertices) + edges_f
    edges_s = [[edges_f[i,0],edges_r[i,0]] for i in range(len(edges_f))]
    edges = np.vstack((edges_f,edges_r,edges_s), dtype=np.uint32)

    surface_f = np.array([[0,i,i+1] for i in index[:-1]]+[[0,index[-1],1]], dtype=np.uint32)
    surface_r = len(front_vertices) + surface_f
    edges_s = np.asarray(edges_s+edges_s[0:1])
    surface_s = [[[edges_s[i,0],edges_s[i,1],edges_s[i+1,0]],
                [edges_s[i,1],edges_s[i+1,0],edges_s[i+1,1]]] for i in range(len(edges_s)-1)]
    surfaces = np.vstack((surface_f,surface_r,*surface_s), dtype=np.uint32)

    vertices = np.vstack((front_vertices,rear_vertices), dtype=np.float32)

    colors = colors
    return vertices, edges, surfaces, colors

def polygon(vertices,colors = [1,0,1,0.5]):
    vertices = np.array(vertices, dtype=np.float32)
    vc = (vertices.max(axis = 0)+vertices.min(axis = 0))/2
    vertices = np.vstack((vc,vertices))
    index = np.arange(1,len(vertices))
    edges = np.array([[i,i+1] for i in index[:-1]]+[[index[-1],1]], dtype=np.uint32)
    surfaces = np.array([[0,i,i+1] for i in index[:-1]]+[[0,index[-1],1]], dtype=np.uint32)
    return vertices, edges, surfaces, colors

class Buffer_obj:
    def __init__(self,vertices, edges, surfaces, colors, offset = False):
        self.vbo,self.ebo,self.sbo = glGenBuffers(3)
        self.vertices, self.edges, self.surfaces, self.colors = vertices, edges, surfaces,colors
        self.num_surfaces,self.num_edges = len(self.surfaces),len(self.edges)
        self.offset = offset
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.edges.nbytes, self.edges, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.sbo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.surfaces.nbytes, self.surfaces, GL_STATIC_DRAW)

    def get_id(self):
        return self.vbo,self.ebo,self.sbo

    def draw(self):
        glPushMatrix()
        glEnableClientState(GL_VERTEX_ARRAY)

        #vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glVertexPointer(3, GL_FLOAT, 0, None)
        #surface
        if self.colors[-1]!=0:
            if self.offset:
                glEnable(GL_POLYGON_OFFSET_FILL)  # 啟用多邊形偏移
                glPolygonOffset(-1,-1)         # 設置偏移值
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glColor4f(*self.colors)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.sbo)
            glDrawElements(GL_TRIANGLES, self.num_surfaces * 3, GL_UNSIGNED_INT, None)
            if self.offset:
                glDisable(GL_POLYGON_OFFSET_FILL) # 禁用多邊形偏移
        #edge
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glColor3f(0, 0, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glDrawElements(GL_LINES, self.num_edges * 2, GL_UNSIGNED_INT, None)

        glDisableClientState(GL_VERTEX_ARRAY)
        glPopMatrix()

class Buffer_rays:
    def __init__(self,rays_data,colors = [0,0,0], width = 1):
        self.vbo = glGenBuffers(1)
        self.colors = colors
        self.width = width
        self.num_rays = len(rays_data)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, rays_data.nbytes, rays_data, GL_STATIC_DRAW)

    def get_id(self):
        return self.vbo,
    
    def draw(self):
        glColor3f(*self.colors)
        glLineWidth(self.width)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glDrawArrays(GL_LINES, 0, self.num_rays*2)
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

class Display3D:
    def __init__(self,width,height,near = 0.1,far = 150):
        self.obj_list = []
        self.windews_size = (width,height)
        self.x0,self.y0,self.z0 = 0,0,-50
        self.h_angle,self.v_angle= 0,0
        self.left_down = False
        self.right_down = False
        self.near,self.far = near,far

        pygame.init()
        pygame.display.set_mode(self.windews_size, DOUBLEBUF | OPENGL)
        glEnable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glEnable(GL_STENCIL_TEST)
        glStencilFunc(GL_ALWAYS, 1, 0xFF)
        glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
        
        glClearColor(1, 1, 1, 1)

    def _mouse_event(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                pygame.quit()
                return False

            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:  # 向上滾動
                    self.z0 += (abs(self.z0)+0.1)*0.02  # 放大
                elif event.y < 0:  # 向下滾動
                    self.z0 -= (abs(self.z0)+0.1)*0.02 # 縮小

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pygame.mouse.get_rel()
                if event.button == 1:
                    self.left_down = True
                elif event.button == 3:
                    self.right_down = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.left_down = False
                elif event.button == 3:
                    self.right_down = False

            elif event.type == pygame.MOUSEMOTION and (self.left_down or self.right_down):
                dx, dy = pygame.mouse.get_rel()
                if self.left_down:
                    self.h_angle += dy * 0.2
                    self.v_angle += dx * 0.2
                elif self.right_down:
                    self.x0 += (dx * abs(self.z0)+0.1) * 0.001
                    self.y0 -= (dy * abs(self.z0)+0.1) * 0.001

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluPerspective(45, (self.windews_size[0] / self.windews_size[1]), self.near, self.far)
        glTranslatef(self.x0, self.y0, self.z0)
        glRotatef(self.h_angle, 1, 0, 0)
        glRotatef(self.v_angle, 0, 1, 0)

        return True

    def add_obj(self,buffer_obj):
        self.obj_list += [buffer_obj]

    def draw_axes(self,scale):
        glLineWidth(2)
        
        #x-axis
        glBegin(GL_LINES)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(scale, 0, 0)
        glVertex3f(scale, 0, 0)
        glVertex3f(0.9*scale, 0.1*scale, 0)
        glVertex3f(scale, 0, 0)
        glVertex3f(0.9*scale, -0.1*scale, 0)
        glEnd()

        #y-axis
        glBegin(GL_LINES)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, scale, 0)
        glVertex3f(0, scale, 0)
        glVertex3f(0.1*scale, 0.9*scale, 0)
        glVertex3f(0, scale, 0)
        glVertex3f(-0.1*scale, 0.9*scale, 0)
        glEnd()

        #z-axis
        glBegin(GL_LINES)
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, scale)
        glVertex3f(0, 0, scale)
        glVertex3f(0.1*scale, 0, 0.9*scale)
        glVertex3f(0, 0, scale)
        glVertex3f(-0.1*scale, 0, 0.9*scale)
        glEnd()

    def draw(self):
        while True :
            if self._mouse_event():
                for obj in self.obj_list:
                    obj.draw()
                    self.draw_axes(abs(0.03*self.z0))
            else:
                break

            pygame.display.flip()
            pygame.time.wait(10)
    
    def close(self):
        for obj in self.obj_list:
            glDeleteBuffers(3, obj.get_id())

# %%
