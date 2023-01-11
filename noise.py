from random import random
from math import cos, pi


def interpolation_lineaire(a, b, t):
	return a * (1 - t) + b * t


def interpolation_cosinusoidale(a, b, t, durete=1):
	return interpolation_lineaire(a, b, (-cos(pi * pow(t, durete)) + 1) / 2)


def interpolation_octave(largeur_fondamentale, hauteur_fondamentale, largeur_tempon, hauteur_tempon, persistance, octave_i, valeurs_octave, tempon):
	# uint32_t x,y;
	# uint32_t xf,yf,xfc,yfc; //Position sur les valeurs aléatoires
	# float xi,yi;    //Position dans l'intervalle entre deux valeurs aléatoires (valeurs comprises entre 0 et 1 )

	largeur_octave = largeur_fondamentale * (octave_i + 1)
	hauteur_octave = hauteur_fondamentale * (octave_i + 1)

	# ----- Génère les valeurs intermédiaires pour arriver au total demandé:
	for y in range(hauteur_tempon):

		yi = y * hauteur_octave / hauteur_tempon
		yf = int(yi)
		yi -= yf
		yfc = (yf + 1) % hauteur_octave

		for x in range(largeur_tempon):
			xi = x * largeur_octave / largeur_tempon
			xf = int(xi)
			xi -= xf
			xfc = (xf + 1) % largeur_octave

			a = valeurs_octave[xf + yf * largeur_octave]
			b = valeurs_octave[xfc + yf * largeur_octave]
			c = valeurs_octave[xf + yfc * largeur_octave]
			d = valeurs_octave[xfc + yfc * largeur_octave]

			i_ab = interpolation_cosinusoidale(a, b, xi)
			i_cd = interpolation_cosinusoidale(c, d, xi)

			intensite = interpolation_cosinusoidale(i_ab, i_cd, yi)

			tempon[x + y * largeur_tempon] += intensite * pow(persistance, octave_i)


def generate_Perlin_2D(largeur_fondamentale, hauteur_fondamentale, largeur_tempon, hauteur_tempon, nbr_octaves, persistance):
	tempon = [0] * largeur_tempon * hauteur_tempon
	octave = []
	amplitude = 0

	for i in range(nbr_octaves):
		octave = []
		# Génère les valeurs de base, comprises entre 0 et 1
		for y in range(hauteur_fondamentale * (i + 1)):
			for x in range(largeur_fondamentale * (i + 1)):
				octave.append(random())

		interpolation_octave(largeur_fondamentale, hauteur_fondamentale, largeur_tempon, hauteur_tempon, persistance, i, octave, tempon)

	# Génère les valeurs finales:
	amplitude = (1 - persistance) / (1 - pow(persistance, nbr_octaves))

	for y in range(hauteur_tempon):
		for x in range(largeur_tempon):
			tempon[x + y * largeur_tempon] = tempon[x + y * largeur_tempon] * amplitude

	return tempon