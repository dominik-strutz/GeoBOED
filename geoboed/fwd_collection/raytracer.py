import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from matplotlib.colors import LinearSegmentedColormap
    import pykonal
except ImportError:
    pass

class TTHelper():
    
    def __init__(self, coord_sys="cartesian") -> None:
        self.coord_sys = coord_sys
        self.model_set = True

    def set_model(self, x, dx, velocity_model,
                  y=np.array([0]), dy=1.0, 
                  z=np.array([0]), dz=1.0):
        self.x, self.y, self.z    = x, y, z
        self.min_coords           = min(x), min(y), min(z)
        self.node_intervals       = dx, dy, dz
        self.dx, self.dy, self.dz = dx, dy, dz
        self.npts                 = len(x), len(y), len(z)
        self.velocity_model       = velocity_model

        self.model_set = True

    def calculate_tt(self, src, rec_list):
        
        solver = pykonal.solver.PointSourceSolver(coord_sys=self.coord_sys)
        solver.velocity.min_coords     = self.min_coords
        solver.velocity.node_intervals = self.node_intervals
        
        solver.velocity.npts           = self.npts
        solver.velocity.values         = self.velocity_model[:, None, :]

        solver.src_loc                 = np.array( (src[0], 0, src[1]) ).astype('double')
                
        solver.solve()
        
        rec_list = np.vstack( [rec_list[:, 0], np.zeros_like(rec_list[:, 0]), rec_list[:, 1]] ).T

        tt_list = solver.traveltime.resample(rec_list.astype('float'))
        
        return tt_list

    def calculate_tt_diff(self, src, rec_list, vpvs_ratio=(np.sqrt(3) - 1)):
        
        tt_list = self.calculate_tt(src, rec_list)
        
        return tt_list * vpvs_ratio
    
    def plot_model(self, prior_realisations=None, pdf_dict=None, pdf_dict_2=None,
                   receivers=None, wells=None, seismic_source=None,
                   xlim=None, ylim=None, colorbar=False,
                   vmin=None, vmax=None, title=None, im_cmap='viridis',
                   plot_rays=None, ax=None, figsize=(16, 7)):
        
        if self.model_set:
                
            if ax is None:
                fig, ax = plt.subplots(figsize=figsize, dpi=200)
            
            im = ax.imshow(self.velocity_model.T/1e3,
                            extent=(min(self.x*1e-3), max(self.x*1e-3),
                                    max(self.z*1e-3), min(self.z*1e-3)),
                            origin='upper', cmap=im_cmap,
                            vmin=vmin/1e3,
                            vmax=vmax/1e3,
                            aspect='auto',
                            zorder=0)
            
            # plot wells
            if wells is not None:
                for mu in wells:
                    ax.plot([mu[0]*1e-3, mu[0]*1e-3], [min(self.z*1e-3), mu[1]*1e-3], linewidth=3, color='k', solid_capstyle='butt', zorder=0)
                ax.plot([], [], linewidth=4, color='k', solid_capstyle='butt', label='well')
            
            if receivers is not None:
                try: 
                    iter(receivers[0])
                except TypeError:
                    receivers = np.array([receivers,])
                    
                ax.scatter(
                    receivers[:,0]*1e-3, receivers[:,1]*1e-3,
                    marker=10, s=200, color='r', zorder=100, clip_on=False, linewidths=0,
                    label='receivers')
            
            if pdf_dict is not None:
                
                alpha_max =  pdf_dict['alpha_max'] if 'alpha_max' in pdf_dict else 1.0
                color_array = plt.get_cmap(pdf_dict['cmap'])(range(256))
                color_array[:,-1] = np.concatenate((np.zeros(50), np.linspace(0.2, alpha_max, 206)), axis=0)
                map_object = LinearSegmentedColormap.from_list(name='Blues_alpha',colors=color_array)

                ax.pcolormesh(pdf_dict['x']*1e-3, pdf_dict['z']*1e-3, pdf_dict['pdf'],
                              cmap=map_object)
                
            if pdf_dict_2 is not None:
                
                alpha_max =  pdf_dict_2['alpha_max'] if 'alpha_max' in pdf_dict else 1.0
                color_array = plt.get_cmap(pdf_dict_2['cmap'])(range(256))
                color_array[:,-1] = np.concatenate((np.zeros(50), np.linspace(0.2, alpha_max, 206)), axis=0)
                map_object = LinearSegmentedColormap.from_list(name='Blues_alpha',colors=color_array)

                ax.pcolormesh(pdf_dict_2['x']*1e-3, pdf_dict_2['z']*1e-3, pdf_dict_2['pdf'],
                              cmap=map_object)  
                
            
            if prior_realisations is not None:
                
                ax.scatter(
                    prior_realisations[:,0]*1e-3, prior_realisations[:,1]*1e-3,
                    marker='+', color='b', linewidths=1, alpha=0.1, zorder=100)
                ax.scatter(
                    [], [],
                    marker='+', color='b', linewidths=1, alpha=0.8, zorder=100,
                    label='prior realisations')
                
                # ax.set_xlim(min(self.x), max(self.x))
                # ax.set_ylim(max(self.z), min(self.z))
            
            if plot_rays is not None and receivers is not None:
                
                # allow  single receiver or list of receivers
                try: 
                    iter(plot_rays[0])
                except TypeError:
                    plot_rays = [plot_rays]
                                
                for src in plot_rays:
                    solver = pykonal.solver.PointSourceSolver(coord_sys=self.coord_sys)
                    solver.velocity.min_coords     = self.min_coords
                    solver.velocity.node_intervals = self.node_intervals
                    solver.velocity.npts           = self.npts
                    solver.velocity.values         = self.velocity_model[:, None, :]

                    solver.src_loc=np.array( (src[0], 0, src[1]) ).astype('double')
                    
                    solver.solve()
                
                    for rec in receivers:
                        ray_coords = solver.traveltime.trace_ray( np.array( [rec[0], 0, rec[1]] , dtype=float) )
                        ax.plot(ray_coords[:, 0]*1e-3, ray_coords[:, 2]*1e-3, 'k', alpha=0.4)
                    
                    ax.plot([], [], 'k', alpha=0.8, label='first arrival ray')
            
            if seismic_source is not None:
                ax.scatter(
                    seismic_source[0]*1e-3, seismic_source[1]*1e-3,
                    marker='*', s=300, color='r', zorder=100, clip_on=False, linewidths=0,
                    label='seismic source')
            
            ax.set_xlabel(r'$x$ [km]')
            ax.set_ylabel(r'$z$ [km]')
            
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
            if colorbar:
                cbar = plt.colorbar(im, fraction=0.046, pad=0.04, ax=ax)
                cbar.set_label('Wavespeed [km/s]')
            if title:
                ax.set_title(title)
            
            if ax is None:
                plt.show()
            else:
                return ax
                    
                    
                    
            