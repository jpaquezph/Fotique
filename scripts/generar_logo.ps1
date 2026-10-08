# Genera los recursos del logo a partir de scripts\logo_fotique.png:
#   fotique\ui\recursos\logo_negro_<escala>.png   (modo claro)
#   fotique\ui\recursos\logo_blanco_<escala>.png  (modo oscuro; el punto no cambia)
#   fotique\ui\recursos\fotique.ico                 (ventanas y ejecutable)
#
# Uso (Windows PowerShell):  .\scripts\generar_logo.ps1
# No necesita nada instalado: usa System.Drawing de .NET.

$raiz = Split-Path -Parent $PSScriptRoot
$origen = Join-Path $PSScriptRoot "logo_fotique.png"
$destino = Join-Path $raiz "fotique\ui\recursos"
New-Item -ItemType Directory -Force $destino | Out-Null

Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;

public static class LogoFotique
{
    // Alto del logo en píxeles lógicos; se genera una imagen por escala de pantalla.
    const int AltoLogico = 56;
    static readonly int[] Escalas = { 100, 125, 150, 175, 200 };
    static readonly int[] TamanosIcono = { 16, 20, 24, 32, 40, 48, 64, 128, 256 };
    static readonly Color FondoIcono = Color.FromArgb(0x17, 0x15, 0x1e);

    public static void Generar(string origen, string destino)
    {
        using (Bitmap negro = Recortar(origen))
        using (Bitmap blanco = Blanquear(negro))
        {
            foreach (int escala in Escalas)
            {
                int alto = AltoLogico * escala / 100;
                using (Bitmap b = Escalar(negro, alto))
                    b.Save(Path.Combine(destino, "logo_negro_" + escala + ".png"), ImageFormat.Png);
                using (Bitmap b = Escalar(blanco, alto))
                    b.Save(Path.Combine(destino, "logo_blanco_" + escala + ".png"), ImageFormat.Png);
            }
            GuardarIcono(blanco, Path.Combine(destino, "fotique.ico"));
        }
    }

    static byte[] Leer(Bitmap b)
    {
        BitmapData d = b.LockBits(new Rectangle(0, 0, b.Width, b.Height),
                                  ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        byte[] datos = new byte[d.Stride * b.Height];
        Marshal.Copy(d.Scan0, datos, 0, datos.Length);
        b.UnlockBits(d);
        return datos;
    }

    static Bitmap Escribir(byte[] datos, int ancho, int alto)
    {
        Bitmap b = new Bitmap(ancho, alto, PixelFormat.Format32bppArgb);
        BitmapData d = b.LockBits(new Rectangle(0, 0, ancho, alto),
                                  ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
        Marshal.Copy(datos, 0, d.Scan0, datos.Length);
        b.UnlockBits(d);
        return b;
    }

    // El original trae mucho margen transparente: se recorta al dibujo.
    static Bitmap Recortar(string ruta)
    {
        using (Bitmap original = new Bitmap(ruta))
        {
            byte[] datos = Leer(original);
            int ancho = original.Width, alto = original.Height;
            int x0 = ancho, y0 = alto, x1 = -1, y1 = -1;
            for (int y = 0; y < alto; y++)
                for (int x = 0; x < ancho; x++)
                    if (datos[(y * ancho + x) * 4 + 3] > 8)
                    {
                        if (x < x0) x0 = x;
                        if (x > x1) x1 = x;
                        if (y < y0) y0 = y;
                        if (y > y1) y1 = y;
                    }
            Rectangle caja = Rectangle.FromLTRB(x0, y0, x1 + 1, y1 + 1);
            return original.Clone(caja, PixelFormat.Format32bppArgb);
        }
    }

    // La letra pasa a blanco; el punto (lo único con color) queda igual.
    static Bitmap Blanquear(Bitmap negro)
    {
        byte[] datos = Leer(negro);
        for (int i = 0; i < datos.Length; i += 4)
        {
            byte azul = datos[i], verde = datos[i + 1], rojo = datos[i + 2];
            bool esPunto = rojo > 110 && rojo - verde > 60;
            if (!esPunto)
                datos[i] = datos[i + 1] = datos[i + 2] = 255;
        }
        return Escribir(datos, negro.Width, negro.Height);
    }

    static Bitmap Escalar(Bitmap origen, int alto)
    {
        int ancho = Math.Max(1, (int)Math.Round(origen.Width * (double)alto / origen.Height));
        Bitmap b = new Bitmap(ancho, alto, PixelFormat.Format32bppArgb);
        using (Graphics g = Graphics.FromImage(b))
        using (ImageAttributes atributos = new ImageAttributes())
        {
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;
            g.CompositingQuality = CompositingQuality.HighQuality;
            atributos.SetWrapMode(WrapMode.TileFlipXY);  // sin halo en los bordes
            g.DrawImage(origen, new Rectangle(0, 0, ancho, alto), 0, 0,
                        origen.Width, origen.Height, GraphicsUnit.Pixel, atributos);
        }
        return b;
    }

    // Ícono: el logo blanco sobre un cuadrado redondeado oscuro, así se ve
    // igual en una barra de tareas clara u oscura.
    static Bitmap Icono(Bitmap blanco, int lado)
    {
        Bitmap b = new Bitmap(lado, lado, PixelFormat.Format32bppArgb);
        using (Graphics g = Graphics.FromImage(b))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;
            float r = lado * 0.22f, d = r * 2, m = lado - d;
            using (GraphicsPath forma = new GraphicsPath())
            using (SolidBrush fondo = new SolidBrush(FondoIcono))
            {
                forma.AddArc(0, 0, d, d, 180, 90);
                forma.AddArc(m, 0, d, d, 270, 90);
                forma.AddArc(m, m, d, d, 0, 90);
                forma.AddArc(0, m, d, d, 90, 90);
                forma.CloseFigure();
                g.FillPath(fondo, forma);
            }
            using (Bitmap logo = Escalar(blanco, Math.Max(8, (int)Math.Round(lado * 0.66))))
                g.DrawImage(logo, (lado - logo.Width) / 2, (lado - logo.Height) / 2,
                            logo.Width, logo.Height);
        }
        return b;
    }

    // .ico con una imagen por tamaño: DIB de 32 bits, salvo 256 px que va en PNG.
    static void GuardarIcono(Bitmap blanco, string ruta)
    {
        List<byte[]> imagenes = new List<byte[]>();
        foreach (int lado in TamanosIcono)
            using (Bitmap b = Icono(blanco, lado))
                imagenes.Add(lado >= 256 ? ComoPng(b) : ComoDib(b));

        using (BinaryWriter w = new BinaryWriter(File.Create(ruta)))
        {
            w.Write((short)0); w.Write((short)1); w.Write((short)TamanosIcono.Length);
            int desplazamiento = 6 + 16 * TamanosIcono.Length;
            for (int i = 0; i < TamanosIcono.Length; i++)
            {
                int lado = TamanosIcono[i];
                w.Write((byte)(lado >= 256 ? 0 : lado));
                w.Write((byte)(lado >= 256 ? 0 : lado));
                w.Write((byte)0); w.Write((byte)0);
                w.Write((short)1); w.Write((short)32);
                w.Write(imagenes[i].Length);
                w.Write(desplazamiento);
                desplazamiento += imagenes[i].Length;
            }
            foreach (byte[] imagen in imagenes)
                w.Write(imagen);
        }
    }

    static byte[] ComoPng(Bitmap b)
    {
        using (MemoryStream m = new MemoryStream())
        {
            b.Save(m, ImageFormat.Png);
            return m.ToArray();
        }
    }

    static byte[] ComoDib(Bitmap b)
    {
        int lado = b.Width;
        byte[] datos = Leer(b);
        int filaMascara = ((lado + 31) / 32) * 4;
        using (MemoryStream m = new MemoryStream())
        using (BinaryWriter w = new BinaryWriter(m))
        {
            w.Write(40); w.Write(lado); w.Write(lado * 2);   // alto doble: color + máscara
            w.Write((short)1); w.Write((short)32);
            w.Write(0); w.Write(lado * lado * 4);
            w.Write(0); w.Write(0); w.Write(0); w.Write(0);
            for (int y = lado - 1; y >= 0; y--)              // de abajo hacia arriba
                w.Write(datos, y * lado * 4, lado * 4);
            w.Write(new byte[filaMascara * lado]);           // la transparencia va en el alfa
            w.Flush();
            return m.ToArray();
        }
    }
}
'@

[LogoFotique]::Generar($origen, $destino)
Get-ChildItem $destino | Select-Object Name, Length
