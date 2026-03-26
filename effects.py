"""
effects.py — JJK Cursed Energy Effects v2
ModernGL + GLSL: glow volumétrico pesado, fundo orgânico.
Pessoa aparece na frente com aura colorida nas bordas.
"""

import moderngl
import numpy as np
import cv2

# ─────────────────────────────────────────────────────────────
# SHADERS GLSL
# ─────────────────────────────────────────────────────────────

_QUAD_VS = """
#version 330
in vec2 in_pos;
void main() { gl_Position = vec4(in_pos, 0.0, 1.0); }
"""

_BG_FS = """
#version 330
uniform float u_time;
uniform vec2  u_res;
out vec4 fragColor;

float hash(vec2 p){ p=fract(p*vec2(127.1,311.7)); p+=dot(p,p+19.19); return fract(p.x*p.y); }
float noise(vec2 p){
    vec2 i=floor(p),f=fract(p); f=f*f*(3.-2.*f);
    return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),
               mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);
}
float fbm(vec2 p, int oct){
    float v=0.,a=.5;
    for(int i=0;i<8;i++){ if(i>=oct) break; v+=a*noise(p); p*=2.1; a*=.5; }
    return v;
}

void main(){
    vec2 uv = gl_FragCoord.xy / u_res;
    vec2 q  = uv * 2.8;
    float n1 = fbm(q + u_time*0.10, 6);
    float n2 = fbm(q + vec2(n1*2.0,n1*1.2) + u_time*0.07, 6);
    float n3 = fbm(q + vec2(n2*1.5,n1*0.8) - u_time*0.05, 5);

    float veins  = pow(clamp(abs(sin(n3*10.+u_time*.25))*n2, 0.,1.), 2.2);
    float veins2 = pow(clamp(abs(sin(n2*16.-u_time*.4)) *n1, 0.,1.), 3.5)*0.5;

    vec3 col = vec3(0.);
    col += vec3(0.70,0.03,0.01)*veins*2.0;
    col += vec3(0.90,0.08,0.02)*veins2*1.5;
    col += vec3(0.18,0.01,0.00)*n2*0.6;

    vec2 vig = uv-0.5;
    col *= clamp(1.-dot(vig,vig)*2.8, 0.,1.);
    col *= 0.82+0.18*sin(u_time*1.6+n1*3.14);

    fragColor = vec4(col, 1.0);
}
"""

_ORB_FS = """
#version 330
uniform float u_time;
uniform vec2  u_res;
uniform vec2  u_center;
uniform vec3  u_color;
uniform float u_radius;
uniform float u_type;
out vec4 fragColor;

float hash(vec2 p){ p=fract(p*vec2(127.1,311.7)); p+=dot(p,p+19.19); return fract(p.x*p.y); }
float noise(vec2 p){
    vec2 i=floor(p),f=fract(p); f=f*f*(3.-2.*f);
    return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),
               mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);
}
float fbm(vec2 p){ float v=0.,a=.5; for(int i=0;i<5;i++){v+=a*noise(p);p*=2.1;a*=.5;} return v; }

float vGlow(float d, float falloff){ return exp(-pow(max(d,0.)/falloff, 1.4)); }

void main(){
    vec2 uv  = gl_FragCoord.xy/u_res;
    float asp= u_res.x/u_res.y;
    vec2 ndc = (uv*2.-1.)*vec2(asp,1.);
    vec2 ctr = u_center*vec2(asp,1.);
    vec2 d   = ndc-ctr;
    float dist = length(d);
    float angle= atan(d.y,d.x);
    float rn   = dist/u_radius;

    // Glow volumétrico (4 camadas)
    float glow = vGlow(dist, u_radius*0.8 )*0.55
               + vGlow(dist, u_radius*1.8 )*0.35
               + vGlow(dist, u_radius*3.5 )*0.20
               + vGlow(dist, u_radius*6.5 )*0.12;

    // Espirais
    float spiral=0.;
    float spd=(u_type<.5)?3.0:-2.5;
    for(int i=0;i<4;i++){
        float ph=float(i)*1.5708;
        float a=angle+ph+u_time*spd;
        float w1=sin(a*5.-rn*15.+u_time*4.);
        float w2=sin(a*9.-rn*10.-u_time*2.5)*.4;
        float msk=smoothstep(2.2,0.,rn)*smoothstep(0.,.3,rn);
        spiral+=max((w1+w2)*msk*.22,0.);
    }

    // Filamentos (16 raios)
    float filament=0.;
    float spd2=(u_type<.5)?2.0:-1.8;
    for(int i=0;i<16;i++){
        float ba=float(i)*0.3927+u_time*spd2;
        float wob=sin(float(i)*1.7+u_time*3.5)*.5;
        float a=ba+wob;
        float diff=abs(mod(angle-a+3.14159,6.28318)-3.14159);
        float lmin=u_radius*.85;
        float lmax=u_radius*(2.2+.6*abs(sin(u_time*4.+float(i)*.9)));
        if(dist>lmin&&dist<lmax){
            float f=smoothstep(.06,0.,diff);
            float fade=1.-(dist-lmin)/(lmax-lmin);
            float pulse=.6+.4*sin(u_time*5.+float(i)*.8);
            filament+=f*fade*pulse*.8;
        }
    }

    // Núcleo
    float tex = fbm(d*10.+u_time*.6)*.35+.65;
    float core= smoothstep(u_radius*1.05,u_radius*.4,dist)*tex;
    float hot = pow(exp(-dist*dist/(u_radius*u_radius*.06)),1.1);

    // Plasma ring
    float ring= exp(-pow(abs(dist-u_radius*.82)/(u_radius*.12),2.))
              *(0.6+0.4*sin(u_time*8.+angle*3.));

    // Anéis orbitais 3D (Gojo)
    float rings=0.;
    if(u_type<.5){
        for(int r=0;r<3;r++){
            float rr=u_radius*(1.6+float(r)*.45);
            float tilt=0.32+float(r)*.12;
            vec2 ep=vec2(d.x,d.y/tilt);
            float ed=abs(length(ep)-rr);
            rings+=exp(-ed*ed*600.)*(0.5+0.5*sin(u_time*(1.2+float(r)*.3)+float(r)*2.1))*.7;
        }
    }

    // Chamas (Sukuna)
    float flames=0.;
    if(u_type>.5){
        float fn=fbm(d*6.-vec2(0.,u_time*2.));
        flames=fn*smoothstep(u_radius*2.5,u_radius*.8,dist)
                 *smoothstep(u_radius*.6,u_radius*1.6,dist)*.7;
    }

    float total=glow+spiral*1.2+filament+core+ring+rings+flames;
    vec3 col=u_color*total + vec3(1.)*hot*1.1;
    col+=vec3(.6,.7,1.)*filament*.3*float(u_type<.5);
    col+=vec3(1.,.5,.2)*filament*.3*float(u_type>.5);
    col=col/(col+vec3(.8));
    col=pow(col,vec3(.85));

    fragColor=vec4(col, clamp(total*.96,0.,1.));
}
"""

_HP_FS = """
#version 330
uniform float u_time;
uniform vec2  u_res;
uniform vec2  u_center;
uniform float u_radius;
out vec4 fragColor;

float hash(vec2 p){ p=fract(p*vec2(127.1,311.7)); p+=dot(p,p+19.19); return fract(p.x*p.y); }
float noise(vec2 p){
    vec2 i=floor(p),f=fract(p); f=f*f*(3.-2.*f);
    return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),
               mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);
}
float fbm(vec2 p){ float v=0.,a=.5; for(int i=0;i<5;i++){v+=a*noise(p);p*=2.2;a*=.5;} return v; }
float vG(float d,float f){ return exp(-pow(max(d,0.)/f,1.4)); }

void main(){
    vec2 uv  = gl_FragCoord.xy/u_res;
    float asp= u_res.x/u_res.y;
    vec2 ndc = (uv*2.-1.)*vec2(asp,1.);
    vec2 ctr = u_center*vec2(asp,1.);
    vec2 d   = ndc-ctr;
    float dist = length(d);
    float angle= atan(d.y,d.x);

    vec3 cBlue  =vec3(.30,.70,1.);
    vec3 cRed   =vec3(1.,.12,.04);
    vec3 cPurple=vec3(.72,.10,1.);

    // Warp pesado
    float wn =fbm(d*2.5+u_time*.35);
    float wn2=fbm(d*4.-vec2(wn,wn*.7)+u_time*.2);
    vec2 warp=d+vec2(wn-.5,wn2-.5)*u_radius*.45;
    float wd =length(warp);

    // Glow enorme
    float bigG=vG(dist,u_radius*8.)*.20+vG(dist,u_radius*4.)*.25+vG(dist,u_radius*2.)*.30;

    // 3 ondas de choque
    float shock=0.;
    for(int k=0;k<3;k++){
        float age=mod(u_time*.7+float(k)*.33,1.);
        float sR=u_radius*(.5+age*7.);
        float sw=u_radius*(.08+age*.15);
        shock+=exp(-abs(dist-sR)/sw)*(1.-age)*.6;
    }

    // Espirais duplas
    float spiral=0.;
    for(int s=0;s<2;s++){
        float off=float(s)*3.14159;
        float spt=(s==0)?u_time*5.:-u_time*4.5;
        for(int i=0;i<80;i++){
            float frac=float(i)/79.;
            float sa=off+spt+frac*5.*3.14159;
            float sr=u_radius*(.05+frac*2.);
            vec2 sp=vec2(cos(sa)*sr,sin(sa)*sr);
            float sd=length(d-sp);
            spiral+=exp(-sd*sd*900.)*(1.-frac)*.9;
        }
    }

    // 32 raios
    float rays=0.;
    for(int i=0;i<32;i++){
        float ba=float(i)*.19635+u_time*3.5;
        float wob=sin(float(i)*1.3+u_time*6.)*.4;
        float a=ba+wob;
        float diff=abs(mod(angle-a+3.14159,6.28318)-3.14159);
        float rl=u_radius*(1.3+1.*abs(sin(u_time*8.+float(i)*.6)));
        if(dist>u_radius*.75&&dist<rl){
            float ray=smoothstep(.10,0.,diff);
            float rfade=1.-(dist-u_radius*.75)/(rl-u_radius*.75);
            float pulse=.5+.5*sin(u_time*9.+float(i)*.7);
            rays+=ray*rfade*pulse*.7;
        }
    }

    float pring=exp(-pow(abs(dist-u_radius*.9)/(u_radius*.10),2.))
               *(.5+.5*sin(u_time*10.+angle*4.));

    float tex =fbm(warp*8.+u_time*.7)*.3+.7;
    float core=smoothstep(u_radius*1.1,u_radius*.5,wd)*tex;
    float hot =pow(exp(-wd*wd/(u_radius*u_radius*.05)),1.1);

    float side=d.x/(u_radius+.001);
    vec3 sCol=mix(cBlue,cRed,.5+.5*sin(angle*3.+u_time*2.));
    sCol=mix(sCol,cPurple,.6);

    vec3 col=cPurple*(bigG+rays+core+pring*.8)+sCol*spiral*1.1
            +vec3(1.)*hot*1.3+vec3(.6,0.,1.)*shock;
    col+=cBlue*core*clamp(-side,0.,1.)*.7;
    col+=cRed *core*clamp( side,0.,1.)*.7;
    col=col/(col+vec3(.6));
    col=pow(col,vec3(.82));

    float alpha=clamp((bigG+spiral*.5+rays*.6+core+hot+shock+pring)*.92,0.,1.);
    fragColor=vec4(col,alpha);
}
"""

# ─────────────────────────────────────────────────────────────
# CLASSE
# ─────────────────────────────────────────────────────────────

class EffectRenderer:
    def __init__(self, width: int, height: int):
        self.W, self.H = width, height

        for backend in ('egl', 'osmesa', None):
            try:
                kw = {'backend': backend} if backend else {}
                self.ctx = moderngl.create_standalone_context(**kw)
                break
            except Exception:
                continue
        else:
            raise RuntimeError("Não foi possível criar contexto OpenGL.")

        self.ctx.enable(moderngl.BLEND)

        self.fbo_tex = self.ctx.texture((width, height), 4)
        self.fbo     = self.ctx.framebuffer(color_attachments=[self.fbo_tex])

        self.prog_bg  = self.ctx.program(vertex_shader=_QUAD_VS, fragment_shader=_BG_FS)
        self.prog_orb = self.ctx.program(vertex_shader=_QUAD_VS, fragment_shader=_ORB_FS)
        self.prog_hp  = self.ctx.program(vertex_shader=_QUAD_VS, fragment_shader=_HP_FS)

        verts = np.array([-1,-1, 1,-1, -1,1, 1,1], dtype='f4')
        self.vbo     = self.ctx.buffer(verts)
        self.vao_bg  = self.ctx.simple_vertex_array(self.prog_bg,  self.vbo, 'in_pos')
        self.vao_orb = self.ctx.simple_vertex_array(self.prog_orb, self.vbo, 'in_pos')
        self.vao_hp  = self.ctx.simple_vertex_array(self.prog_hp,  self.vbo, 'in_pos')

    def _ndc(self, px, py):
        return ((px/self.W)*2.-1., -((py/self.H)*2.-1.))

    def _pr(self, px_r):
        return (px_r/self.W)*2.

    # ── Efeitos GL ───────────────────────────────────────────
    def _render_effects(self, state, t):
        res = [float(self.W), float(self.H)]
        self.fbo.use()
        self.fbo.clear(0,0,0,0)

        # Fundo: blend normal
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.prog_bg['u_time'].value = t
        self.prog_bg['u_res'].value  = res
        self.vao_bg.render(moderngl.TRIANGLE_STRIP)

        # Bolas: additive
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE

        if state.get('blue_active') and not state.get('hollow_active'):
            cx,cy = self._ndc(*state['blue_pos'])
            self.prog_orb['u_time'].value   = t
            self.prog_orb['u_res'].value    = res
            self.prog_orb['u_center'].value = (cx,cy)
            self.prog_orb['u_color'].value  = (0.30,0.72,1.0)
            self.prog_orb['u_radius'].value = self._pr(44)
            self.prog_orb['u_type'].value   = 0.0
            self.vao_orb.render(moderngl.TRIANGLE_STRIP)

        if state.get('red_active') and not state.get('hollow_active'):
            cx,cy = self._ndc(*state['red_pos'])
            self.prog_orb['u_time'].value   = t
            self.prog_orb['u_res'].value    = res
            self.prog_orb['u_center'].value = (cx,cy)
            self.prog_orb['u_color'].value  = (1.0,0.14,0.03)
            self.prog_orb['u_radius'].value = self._pr(44)
            self.prog_orb['u_type'].value   = 1.0
            self.vao_orb.render(moderngl.TRIANGLE_STRIP)

        if state.get('hollow_active'):
            cx,cy = self._ndc(*state['hollow_pos'])
            self.prog_hp['u_time'].value   = t
            self.prog_hp['u_res'].value    = res
            self.prog_hp['u_center'].value = (cx,cy)
            self.prog_hp['u_radius'].value = self._pr(62)
            self.vao_hp.render(moderngl.TRIANGLE_STRIP)

        raw = self.fbo_tex.read()
        img = np.frombuffer(raw, dtype=np.uint8).reshape(self.H, self.W, 4)
        return np.flipud(img)

    # ── Aura na silhueta ─────────────────────────────────────
    @staticmethod
    def _person_with_aura(mask_f, frame_bgr, state):
        """
        mask_f   : float32 H×W  (1 = pessoa)
        Retorna  : float32 H×W×3 BGR  +  float32 H×W alpha
        """
        # Cor da aura por estado
        if state.get('hollow_active'):
            aura_bgr = np.array([220, 50, 200], dtype=np.float32)
        elif state.get('blue_active') and state.get('red_active'):
            aura_bgr = np.array([200, 80, 255], dtype=np.float32)
        elif state.get('blue_active'):
            aura_bgr = np.array([255, 150, 40],  dtype=np.float32)
        elif state.get('red_active'):
            aura_bgr = np.array([30,  30,  255], dtype=np.float32)
        else:
            aura_bgr = np.array([160, 160, 210], dtype=np.float32)

        mask_u8   = (np.clip(mask_f, 0, 1) * 255).astype(np.uint8)
        mask_soft = cv2.GaussianBlur(mask_u8, (15,15), 0)

        # Bordas da silhueta
        k_small  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15))
        k_large  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(35,35))
        dilated  = cv2.dilate(mask_u8, k_large,  iterations=2)
        eroded   = cv2.erode (mask_u8, k_small,  iterations=1)
        border_f = np.clip((dilated.astype(np.float32) - eroded.astype(np.float32))/255., 0,1)

        # Glow suave ao redor
        glow_f   = cv2.GaussianBlur(border_f, (71,71), 0)
        glow_f   = np.clip(glow_f * 2.5, 0, 1)

        # Pessoa BGR
        person_f = frame_bgr.astype(np.float32)

        # Aplica aura: soma cor da aura nas bordas e no glow externo
        aura_layer = (border_f[:,:,np.newaxis] * aura_bgr * 4.0
                    + glow_f[:,:,np.newaxis]   * aura_bgr * 2.0)
        person_lit = np.clip(person_f + aura_layer, 0, 255)

        # Alpha final: pessoa opaca + halo semi-transparente
        alpha = np.clip(mask_soft.astype(np.float32)/255. + glow_f*0.9, 0, 1)

        return person_lit, alpha

    # ── Render principal ─────────────────────────────────────
    def render(self, frame_bgr, state, t):
        """
        frame_bgr : (H,W,3) uint8 — webcam espelhada
        state     : dict de estado
        t         : float segundos
        """
        # 1. Efeitos GL → BGR
        effects_rgba = self._render_effects(state, t)
        effects_bgr  = cv2.cvtColor(effects_rgba, cv2.COLOR_RGBA2BGR).astype(np.float32)

        # 2. Sua imagem levemente escurecida (fundo JJK domina, você aparece nítido)
        person = frame_bgr.astype(np.float32) * 0.82

        # Onde as orbes brilham, ilumina levemente você também
        effect_lum = effects_bgr.mean(axis=2, keepdims=True) / 255.0
        person = np.clip(person + effect_lum * 20.0, 0, 255)

        # Composição final: efeitos atrás + você na frente
        final = np.clip(effects_bgr * 0.55 + person * 0.70, 0, 255)
        return final.astype(np.uint8)

    def release(self):
        self.ctx.release()