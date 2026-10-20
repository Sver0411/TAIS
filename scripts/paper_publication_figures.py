"""Presentation-only exports from frozen summary CSV; no re-scoring/interpolation."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def render(out,analysis=None):
    analysis=analysis or ROOT/'results/tais-paper/test/analysis'
    data=pd.read_csv(analysis/'summary.csv')
    plt.rcParams.update({'font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8})
    for view in ['native','common']:
        d={r['method']:r for r in data[(data['view']==view)&(data.group=='overall')].to_dict('records')}
        fig,axes=plt.subplots(2,2,figsize=(7.6,6.3));pairs=[('samples','recall'),('samples','f1'),('binary_v1_bytes','f1'),('samples','fault_induced_false')]
        handles=[];labels=[]
        for ax,(x,y) in zip(axes.flat,pairs):
            for color,kind,short in [('#666666','Fixed','Fixed'),('#e69f00','Delta','Delta'),('#0072b2','Variance','Variance'),('#009e73','Rao-inspired','Rao-inspired')]:
                names=[f'Fixed-{c}' for c in [5,10,20,30,40,60]] if kind=='Fixed' else [f'{kind}-c{c}' for c in [20,40,60]]
                if view=='native':names=[n+'+C11' for n in names]
                xx=[d[n][x]/1000 for n in names];yy=[d[n][y]*(100 if y in ['recall','f1'] else 1) for n in names]
                h=ax.scatter(xx,yy,c=color,s=24,label=short,alpha=.9)
                for n,xv,yv in zip(names,xx,yy):ax.annotate(n.split('+')[0].rsplit('-',1)[1].replace('c',''),(xv,yv),fontsize=6.5,xytext=(3,2),textcoords='offset points')
            points=[('s','#cc79a7','GateOnly','Gate'),('x','#cc79a7','GateOnly+U','Gate+U'),('v','#882255','JO-S','JO-S'),('^','#d55e00','JO-SU-20','SU20'),('D','#d55e00','JO-SU-30','SU30'),('*','#d55e00','JO-SU-40','SU40'),('P','#000000','AdaptiveSense+TrustLog','AS+C11')]
            for marker,color,m,label in points:
                r=d[m];ax.scatter(r[x]/1000,r[y]*(100 if y in ['recall','f1'] else 1),marker=marker,c=color,s=38,label=label,zorder=3)
            ax.set_xlabel('Sample cycles (thousands)' if x=='samples' else 'Binary v1 bytes (thousands)');ax.set_ylabel({'recall':'Recall (%)','f1':'F1 (%)','fault_induced_false':'Fault-induced false reports'}[y]);ax.grid(alpha=.2)
        handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=6,fontsize=7,frameon=False,columnspacing=.9,handletextpad=.3)
        fig.subplots_adjust(left=.09,right=.99,top=.95,bottom=.15,hspace=.38,wspace=.32)
        fig.savefig(out/f'{view}_tradeoffs.png',dpi=300);plt.close(fig)
    # Same stored grid; rendering only, no new coefficients or empirical claims.
    grid=pd.read_csv(analysis/'resource_sensitivity.csv');fig,axes=plt.subplots(1,3,figsize=(7.6,2.65))
    for ax,(name,title) in zip(axes,[('GateOnly','Gate'),('Fixed-30+C11','Fixed30+C11'),('Variance-budget-SU40+C11','Variance SU40 budget')]):
        r=grid[grid.comparator==name];x=np.sort(r.sample_per_byte.unique());y=np.sort(r.tx_fixed_per_byte.unique());z=r.pivot(index='tx_fixed_per_byte',columns='sample_per_byte',values='su40_cost_ratio').to_numpy()
        im=ax.pcolormesh(x,y,z,shading='auto',cmap='RdBu_r',vmin=.5,vmax=1.5)
        if z.min()<1<z.max():ax.contour(x,y,z,levels=[1],colors='k',linewidths=.6)
        ax.set(xscale='log',yscale='log',title='SU40 / '+title,xlabel='Sample / byte cost')
        ax.set_ylabel('Fixed TX / byte cost');ax.tick_params(labelsize=7)
    fig.subplots_adjust(left=.08,right=.91,bottom=.22,top=.83,wspace=.45);cax=fig.add_axes([.93,.23,.015,.58]);fig.colorbar(im,cax=cax).set_label('Cost ratio',fontsize=8)
    fig.savefig(out/'resource_sensitivity.png',dpi=300);plt.close(fig)

if __name__=='__main__':render(ROOT/'papers/tais/figures')
