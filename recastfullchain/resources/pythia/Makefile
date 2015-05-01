all:
	c++ -O2 -ansi -pedantic -W -Wall -Wshadow -m64 -Wno-shadow `pythia8-config --cxxflags` \
		  pythiarun.cxx -o pythiarun \
		  `pythia8-config --libs --hepmc|sed 's|\-lhepmcinterface||'` \
      -lpythia8tohepmc \
      -L`pythia8-config --libdir`/archive 